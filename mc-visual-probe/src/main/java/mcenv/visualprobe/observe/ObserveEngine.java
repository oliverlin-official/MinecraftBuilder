package mcenv.visualprobe.observe;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import mcenv.visualprobe.api.ProbeException;
import mcenv.visualprobe.camera.CameraBackend;
import mcenv.visualprobe.camera.CameraPose;
import mcenv.visualprobe.camera.SpectatorCameraBackend;
import mcenv.visualprobe.capture.CaptureMetadata;
import mcenv.visualprobe.capture.ScreenshotService;
import mcenv.visualprobe.render.ChunkReadiness;
import mcenv.visualprobe.render.VisualProfile;
import mcenv.visualprobe.sync.WorldRevisionFence;
import net.minecraft.client.MinecraftClient;
import net.minecraft.client.network.ClientPlayerEntity;
import net.minecraft.client.world.ClientWorld;
import net.minecraft.server.integrated.IntegratedServer;
import net.minecraft.server.network.ServerPlayerEntity;
import net.minecraft.server.world.ServerWorld;
import net.minecraft.world.GameMode;

import java.nio.file.Path;
import java.time.Instant;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.atomic.AtomicInteger;

public final class ObserveEngine {
	private static final int DEFAULT_CHUNK_RADIUS = 3;
	private static final int DEFAULT_STABLE_TICKS = 12;
	private static final long DEFAULT_TIMEOUT_MS = 15_000L;

	private final CameraBackend backend;
	private final ScreenshotService screenshots;
	private final AtomicInteger captureSeq = new AtomicInteger();
	private final Object lock = new Object();
	private Job job;
	private volatile String lastError;

	public ObserveEngine(CameraBackend backend, ScreenshotService screenshots) {
		this.backend = backend;
		this.screenshots = screenshots;
	}

	public String backendId() {
		return backend.id();
	}

	public boolean isCapturing() {
		synchronized (lock) {
			return job != null;
		}
	}

	public String lastError() {
		return lastError;
	}

	public CompletableFuture<JsonObject> submitObserve(JsonObject request) {
		CompletableFuture<JsonObject> future = new CompletableFuture<>();
		synchronized (lock) {
			if (job != null) {
				future.completeExceptionally(ProbeException.busy());
				return future;
			}
			job = new Job(request, future);
		}
		return future;
	}

	public JsonObject status(MinecraftClient client) {
		JsonObject json = new JsonObject();
		json.addProperty("minecraft_version", client.getGameVersion());
		json.addProperty("camera_backend", backend.id());
		json.addProperty("render_profile", "PRODUCTION");
		json.addProperty("world_revision", 0);
		boolean worldLoaded = client.world != null && client.player != null;
		json.addProperty("world_loaded", worldLoaded);
		if (client.world != null) {
			json.addProperty("dimension", client.world.getRegistryKey().getValue().toString());
		}
		if (isCapturing()) {
			json.addProperty("status", "CAPTURING");
		} else if (!worldLoaded) {
			json.addProperty("status", client.world != null ? "LOADING" : "NO_WORLD");
		} else if (lastError != null) {
			json.addProperty("status", "READY");
			json.addProperty("last_error", lastError);
		} else {
			json.addProperty("status", "READY");
		}
		return json;
	}

	public JsonObject currentPoseJson(MinecraftClient client) throws ProbeException {
		if (client.world == null || client.player == null) {
			throw ProbeException.noWorld();
		}
		int fov = client.options.getFov().getValue();
		return backend.readback(client, fov).toJson();
	}

	public void tick(MinecraftClient client) {
		Job active;
		synchronized (lock) {
			active = job;
		}
		if (active == null) {
			return;
		}
		try {
			active.tick(client);
		} catch (ProbeException e) {
			fail(active, e);
		} catch (RuntimeException e) {
			fail(active, ProbeException.screenshotFailed(e.getMessage() == null ? e.getClass().getSimpleName() : e.getMessage()));
		}
	}

	private void succeed(Job finished, JsonObject result) {
		synchronized (lock) {
			if (job == finished) {
				job = null;
			}
		}
		lastError = null;
		finished.future.complete(result);
	}

	private void fail(Job finished, ProbeException error) {
		synchronized (lock) {
			if (job == finished) {
				job = null;
			}
		}
		lastError = error.code() + ": " + error.getMessage();
		try {
			VisualProfile.restore(MinecraftClient.getInstance(), finished.appliedProfile);
		} catch (RuntimeException ignored) {
		}
		finished.future.completeExceptionally(error);
	}

	private final class Job {
		private final JsonObject request;
		private final CompletableFuture<JsonObject> future;
		private final long startedAt = System.nanoTime();
		private final long timeoutNs;
		private Phase phase = Phase.START;
		private CameraPose requestedPose;
		private String observationId;
		private int worldRevision;
		private int chunkRadius;
		private int stableTicksRequired;
		private int stableTicks;
		private int waitTicks;
		private boolean hideHud;
		private VisualProfile.Id profileId;
		private VisualProfile.Applied appliedProfile;
		private List<WorldRevisionFence.Anchor> anchors = List.of();
		private Path outputRoot;
		private PlayerSnapshot restorePlayer;
		private int loadedRadius = -1;
		private CompletableFuture<ScreenshotService.Result> screenshotFuture;
		private Path pngPath;
		private Path metaPath;
		private String captureId;

		private Job(JsonObject request, CompletableFuture<JsonObject> future) {
			this.request = request;
			this.future = future;
			long timeoutMs = request.has("timeout_ms") ? request.get("timeout_ms").getAsLong() : DEFAULT_TIMEOUT_MS;
			this.timeoutNs = Math.max(1_000L, timeoutMs) * 1_000_000L;
		}

		private void tick(MinecraftClient client) throws ProbeException {
			if (System.nanoTime() - startedAt > timeoutNs) {
				if (phase == Phase.WAIT_CHUNKS) {
					throw ProbeException.chunkTimeout(Math.max(loadedRadius, 0), chunkRadius);
				}
				if (phase == Phase.WAIT_UNPAUSED) {
					throw ProbeException.captureTimeout("Game stayed paused or a screen stayed open. Close the pause menu and keep the window unpaused.");
				}
				throw ProbeException.captureTimeout("Observation timed out during " + phase);
			}
			switch (phase) {
				case START -> start(client);
				case WAIT_UNPAUSED -> waitUnpaused(client);
				case APPLY_POSE -> applyPose(client);
				case WAIT_POSE -> waitPose(client);
				case WAIT_CHUNKS -> waitChunks(client);
				case WAIT_SYNC -> waitSync(client);
				case WAIT_STABLE -> waitStable(client);
				case CAPTURE -> capture(client);
				case WAIT_SCREENSHOT -> waitScreenshot(client);
				case DONE -> {
				}
			}
		}

		private void start(MinecraftClient client) throws ProbeException {
			if (client.world == null || client.player == null) {
				throw ProbeException.noWorld();
			}
			try {
				requestedPose = CameraPose.fromJson(request);
			} catch (RuntimeException e) {
				throw ProbeException.invalidPose(e.getMessage());
			}
			if (!Double.isFinite(requestedPose.x()) || !Double.isFinite(requestedPose.y()) || !Double.isFinite(requestedPose.z())) {
				throw ProbeException.invalidPose("Pose coordinates must be finite.");
			}
			observationId = sanitizeObservationId(
				request.has("observation_id") ? request.get("observation_id").getAsString() : "OBS_UNTITLED"
			);
			worldRevision = request.has("expected_world_revision")
				? request.get("expected_world_revision").getAsInt()
				: 0;
			chunkRadius = request.has("required_chunk_radius")
				? request.get("required_chunk_radius").getAsInt()
				: DEFAULT_CHUNK_RADIUS;
			stableTicksRequired = request.has("stable_ticks")
				? request.get("stable_ticks").getAsInt()
				: DEFAULT_STABLE_TICKS;
			hideHud = !request.has("hide_hud") || request.get("hide_hud").getAsBoolean();
			profileId = VisualProfile.parse(
				request.has("render_profile") ? request.get("render_profile").getAsString() : "PRODUCTION"
			);
			anchors = WorldRevisionFence.parse(request);
			outputRoot = resolveOutputRoot(client, request);
			restorePlayer = PlayerSnapshot.capture(client);
			appliedProfile = VisualProfile.apply(client, profileId, requestedPose.fov(), hideHud);
			waitTicks = 0;
			phase = Phase.WAIT_UNPAUSED;
		}

		private void waitUnpaused(MinecraftClient client) {
			if (!VisualProfile.worldViewReady(client)) {
				waitTicks++;
				return;
			}
			waitTicks++;
			if (waitTicks >= 8) {
				phase = Phase.APPLY_POSE;
				waitTicks = 0;
			}
		}

		private void applyPose(MinecraftClient client) throws ProbeException {
			backend.apply(client, requestedPose);
			waitTicks = 0;
			phase = Phase.WAIT_POSE;
		}

		private void waitPose(MinecraftClient client) throws ProbeException {
			if (!VisualProfile.worldViewReady(client)) {
				return;
			}
			holdCamera(client, true);
			waitTicks++;
			CameraPose actual = backend.readback(client, requestedPose.fov());
			if (requestedPose.matches(actual, 0.25, 1.0f)) {
				phase = Phase.WAIT_CHUNKS;
				waitTicks = 0;
			}
		}

		private void waitChunks(MinecraftClient client) throws ProbeException {
			if (!VisualProfile.worldViewReady(client)) {
				return;
			}
			holdCamera(client, waitTicks % 10 == 0);
			waitTicks++;
			ClientWorld world = client.world;
			if (world == null) {
				throw ProbeException.noWorld();
			}
			boolean wait = !request.has("wait_for_chunks") || request.get("wait_for_chunks").getAsBoolean();
			loadedRadius = ChunkReadiness.loadedRadius(world, requestedPose.x(), requestedPose.z(), chunkRadius);
			if (!wait || loadedRadius >= chunkRadius) {
				phase = Phase.WAIT_SYNC;
				waitTicks = 0;
			}
		}

		private void waitSync(MinecraftClient client) throws ProbeException {
			if (!VisualProfile.worldViewReady(client)) {
				return;
			}
			holdCamera(client, false);
			if (anchors.isEmpty()) {
				phase = Phase.WAIT_STABLE;
				stableTicks = 0;
				return;
			}
			String mismatch = WorldRevisionFence.firstMismatch(client.world, anchors);
			if (mismatch == null) {
				phase = Phase.WAIT_STABLE;
				stableTicks = 0;
				return;
			}
			waitTicks++;
			if (waitTicks > 80) {
				throw ProbeException.worldNotSynced(mismatch);
			}
		}

		private void waitStable(MinecraftClient client) {
			if (!VisualProfile.worldViewReady(client)) {
				stableTicks = 0;
				return;
			}
			holdCamera(client, false);
			stableTicks++;
			if (stableTicks >= stableTicksRequired) {
				phase = Phase.CAPTURE;
			}
		}

		private void holdCamera(MinecraftClient client, boolean syncServer) {
			if (backend instanceof SpectatorCameraBackend spectator) {
				spectator.hold(client, requestedPose);
				if (syncServer) {
					try {
						spectator.apply(client, requestedPose);
					} catch (ProbeException ignored) {
					}
				}
			}
		}

		private void capture(MinecraftClient client) throws ProbeException {
			if (!VisualProfile.worldViewReady(client)) {
				phase = Phase.WAIT_STABLE;
				stableTicks = 0;
				return;
			}
			holdCamera(client, true);
			captureId = String.format(Locale.ROOT, "cap_%06d", captureSeq.incrementAndGet());
			Path obsDir = outputRoot.resolve("observations").resolve(observationId);
			pngPath = obsDir.resolve(captureId + ".png");
			metaPath = obsDir.resolve(captureId + ".json");
			screenshotFuture = screenshots.capture(client, pngPath);
			phase = Phase.WAIT_SCREENSHOT;
		}

		private void waitScreenshot(MinecraftClient client) throws ProbeException {
			holdCamera(client, false);
			if (screenshotFuture == null) {
				throw ProbeException.screenshotFailed("Screenshot was not started.");
			}
			if (!screenshotFuture.isDone()) {
				return;
			}
			ScreenshotService.Result shot;
			try {
				shot = screenshotFuture.getNow(null);
			} catch (Exception e) {
				Throwable cause = e.getCause() == null ? e : e.getCause();
				if (cause instanceof ProbeException probe) {
					throw probe;
				}
				throw ProbeException.screenshotFailed(cause.getMessage());
			}
			if (shot == null) {
				throw ProbeException.screenshotFailed("Screenshot completed without an image.");
			}
			finishCapture(client, shot);
		}

		private void finishCapture(MinecraftClient client, ScreenshotService.Result shot) throws ProbeException {
			CameraPose actual = backend.readback(client, client.options.getFov().getValue());
			try {
				VisualProfile.restore(client, appliedProfile);
				if (restorePlayer != null) {
					restorePlayer.restore(client);
				}
			} catch (RuntimeException ignored) {
			}
			ClientWorld world = client.world;
			String dimension = world != null ? world.getRegistryKey().getValue().toString() : "unknown";
			long time = world != null ? world.getTimeOfDay() : 0L;
			String weather = "clear";
			if (world != null) {
				weather = world.isThundering() ? "thunder" : world.isRaining() ? "rain" : "clear";
			}
			int viewDistance = client.options.getViewDistance().getValue();
			CaptureMetadata metadata = new CaptureMetadata(
				captureId,
				observationId,
				worldRevision,
				actual,
				profileId.name(),
				new int[] {shot.width(), shot.height()},
				viewDistance,
				true,
				dimension,
				time,
				weather,
				Instant.now().toString(),
				client.getGameVersion(),
				backend.id(),
				shot.path().toAbsolutePath().toString()
			);
			try {
				metadata.write(metaPath);
			} catch (Exception e) {
				throw ProbeException.screenshotFailed("Could not write metadata: " + e.getMessage());
			}
			JsonObject result = new JsonObject();
			result.addProperty("status", "OK");
			result.addProperty("capture_id", captureId);
			result.addProperty("observation_id", observationId);
			result.addProperty("file", metadata.pngPath());
			result.addProperty("png_path", metadata.pngPath());
			result.addProperty("metadata_file", metaPath.toAbsolutePath().toString());
			result.add("requested_pose", requestedPose.toJson());
			result.add("actual_pose", actual.toJson());
			result.addProperty("minecraft_version", metadata.minecraftVersion());
			result.addProperty("dimension", dimension);
			JsonArray resolution = new JsonArray();
			resolution.add(shot.width());
			resolution.add(shot.height());
			result.add("resolution", resolution);
			result.addProperty("timestamp", metadata.timestamp());
			result.addProperty("world_revision", worldRevision);
			result.addProperty("camera_backend", backend.id());
			phase = Phase.DONE;
			succeed(this, result);
		}
	}

	private enum Phase {
		START, WAIT_UNPAUSED, APPLY_POSE, WAIT_POSE, WAIT_CHUNKS, WAIT_SYNC, WAIT_STABLE, CAPTURE, WAIT_SCREENSHOT, DONE
	}

	private static String sanitizeObservationId(String raw) {
		String cleaned = raw.replaceAll("[^A-Za-z0-9._-]", "_");
		if (cleaned.isBlank()) {
			return "OBS_UNTITLED";
		}
		return cleaned.length() > 64 ? cleaned.substring(0, 64) : cleaned;
	}

	private static Path resolveOutputRoot(MinecraftClient client, JsonObject request) {
		if (request.has("output_dir") && !request.get("output_dir").getAsString().isBlank()) {
			return Path.of(request.get("output_dir").getAsString()).toAbsolutePath().normalize();
		}
		return client.runDirectory.toPath().resolve("visual-probe").toAbsolutePath().normalize();
	}

	private record PlayerSnapshot(double x, double y, double z, float yaw, float pitch, GameMode gameMode) {
		static PlayerSnapshot capture(MinecraftClient client) {
			ClientPlayerEntity player = client.player;
			GameMode mode = client.interactionManager != null
				? client.interactionManager.getCurrentGameMode()
				: GameMode.SURVIVAL;
			return new PlayerSnapshot(player.getX(), player.getY(), player.getZ(), player.getYaw(), player.getPitch(), mode);
		}

		void restore(MinecraftClient client) {
			IntegratedServer server = client.getServer();
			if (server == null || client.player == null) {
				return;
			}
			UUID uuid = client.player.getUuid();
			server.execute(() -> {
				ServerPlayerEntity player = server.getPlayerManager().getPlayer(uuid);
				if (player == null) {
					return;
				}
				if (player.getEntityWorld() instanceof ServerWorld world) {
					player.teleport(world, x, y, z, Set.of(), yaw, pitch, false);
				}
				if (gameMode != null) {
					player.changeGameMode(gameMode);
				}
			});
		}
	}
}
