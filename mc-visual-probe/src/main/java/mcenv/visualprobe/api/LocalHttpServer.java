package mcenv.visualprobe.api;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.google.gson.JsonSyntaxException;
import mcenv.visualprobe.VisualProbeClient;
import mcenv.visualprobe.observe.ObserveEngine;
import net.minecraft.client.MinecraftClient;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.SecureRandom;
import java.util.HexFormat;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;

import com.sun.net.httpserver.Headers;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;

public final class LocalHttpServer {
	public static final int PORT = Integer.getInteger("mc-visual-probe.port", 8765);
	private static final Gson GSON = new GsonBuilder().setPrettyPrinting().create();

	private final ObserveEngine engine;
	private final String token;
	private HttpServer server;

	public LocalHttpServer(ObserveEngine engine) {
		this.engine = engine;
		this.token = generateToken();
	}

	public void start() {
		try {
			server = HttpServer.create(new InetSocketAddress(InetAddress.getByName("127.0.0.1"), PORT), 0);
		} catch (IOException e) {
			VisualProbeClient.LOGGER.error("Could not bind visual probe to 127.0.0.1:{}", PORT, e);
			return;
		}
		server.createContext("/v1/status", this::handleStatus);
		server.createContext("/v1/observe", this::handleObserve);
		server.createContext("/v1/camera/pose", this::handlePose);
		server.setExecutor(runnable -> {
			Thread thread = new Thread(runnable, "mc-visual-probe-http");
			thread.setDaemon(true);
			thread.start();
		});
		server.start();
		writeSessionFile();
		VisualProbeClient.LOGGER.info("Visual Probe listening on http://127.0.0.1:{}", PORT);
	}

	public void stop() {
		if (server != null) {
			server.stop(0);
			server = null;
		}
	}

	private void handleStatus(HttpExchange exchange) throws IOException {
		if (!"GET".equalsIgnoreCase(exchange.getRequestMethod())) {
			sendJson(exchange, 405, errorJson("METHOD_NOT_ALLOWED", "Use GET"));
			return;
		}
		if (!authorized(exchange)) {
			sendUnauthorized(exchange);
			return;
		}
		try {
			sendJson(exchange, 200, runOnClient(engine::status, 2, TimeUnit.SECONDS));
		} catch (Exception e) {
			sendException(exchange, e);
		}
	}

	private void handlePose(HttpExchange exchange) throws IOException {
		if (!authorized(exchange)) {
			sendUnauthorized(exchange);
			return;
		}
		try {
			if ("GET".equalsIgnoreCase(exchange.getRequestMethod())) {
				sendJson(exchange, 200, runOnClient(engine::currentPoseJson, 3, TimeUnit.SECONDS));
				return;
			}
			sendJson(exchange, 405, errorJson("METHOD_NOT_ALLOWED", "Use GET. Pose changes are applied via POST /v1/observe."));
		} catch (Exception e) {
			sendException(exchange, e);
		}
	}

	private void handleObserve(HttpExchange exchange) throws IOException {
		if (!"POST".equalsIgnoreCase(exchange.getRequestMethod())) {
			sendJson(exchange, 405, errorJson("METHOD_NOT_ALLOWED", "Use POST"));
			return;
		}
		if (!authorized(exchange)) {
			sendUnauthorized(exchange);
			return;
		}
		JsonObject body;
		try {
			body = readJson(exchange);
		} catch (ProbeException e) {
			sendJson(exchange, e.httpStatus(), errorJson(e.code(), e.getMessage()));
			return;
		}
		long timeoutMs = body.has("timeout_ms") ? body.get("timeout_ms").getAsLong() : 15_000L;
		CompletableFuture<JsonObject> future = engine.submitObserve(body);
		try {
			JsonObject result = future.get(timeoutMs + 2_000L, TimeUnit.MILLISECONDS);
			sendJson(exchange, 200, result);
		} catch (TimeoutException e) {
			sendJson(exchange, 504, errorJson("CAPTURE_TIMEOUT", "HTTP wait exceeded observation timeout."));
		} catch (Exception e) {
			sendException(exchange, e);
		}
	}

	@FunctionalInterface
	private interface ClientCall {
		JsonObject run(MinecraftClient client) throws ProbeException;
	}

	private static JsonObject runOnClient(ClientCall call, long timeout, TimeUnit unit) throws Exception {
		MinecraftClient client = MinecraftClient.getInstance();
		CompletableFuture<JsonObject> future = new CompletableFuture<>();
		client.execute(() -> {
			try {
				future.complete(call.run(client));
			} catch (Throwable t) {
				future.completeExceptionally(t);
			}
		});
		return future.get(timeout, unit);
	}

	private boolean authorized(HttpExchange exchange) {
		Headers headers = exchange.getRequestHeaders();
		String provided = headers.getFirst("X-Visual-Probe-Token");
		if (provided == null || provided.isBlank()) {
			String auth = headers.getFirst("Authorization");
			if (auth != null && auth.regionMatches(true, 0, "Bearer ", 0, 7)) {
				provided = auth.substring(7).trim();
			}
		}
		if (provided == null) {
			return false;
		}
		byte[] expected = token.getBytes(StandardCharsets.UTF_8);
		byte[] actual = provided.getBytes(StandardCharsets.UTF_8);
		if (expected.length != actual.length) {
			return false;
		}
		int diff = 0;
		for (int i = 0; i < expected.length; i++) {
			diff |= expected[i] ^ actual[i];
		}
		return diff == 0;
	}

	private void sendUnauthorized(HttpExchange exchange) throws IOException {
		sendJson(exchange, 401, errorJson("UNAUTHORIZED", "Missing or invalid session token."));
	}

	private static JsonObject readJson(HttpExchange exchange) throws ProbeException, IOException {
		try (InputStream in = exchange.getRequestBody()) {
			byte[] bytes = in.readAllBytes();
			if (bytes.length == 0) {
				throw new ProbeException("CAMERA_POSE_INVALID", 400, "Request body is empty.");
			}
			return JsonParser.parseString(new String(bytes, StandardCharsets.UTF_8)).getAsJsonObject();
		} catch (JsonSyntaxException e) {
			throw new ProbeException("CAMERA_POSE_INVALID", 400, "Request body is not valid JSON.");
		}
	}

	private static void sendException(HttpExchange exchange, Exception e) throws IOException {
		ProbeException probe = unwrap(e);
		if (probe != null) {
			sendJson(exchange, probe.httpStatus(), errorJson(probe.code(), probe.getMessage()));
			return;
		}
		String message = e.getMessage() == null ? e.getClass().getSimpleName() : e.getMessage();
		sendJson(exchange, 500, errorJson("ERROR", message));
	}

	private static ProbeException unwrap(Throwable error) {
		Throwable current = error;
		while (current != null) {
			if (current instanceof ProbeException probe) {
				return probe;
			}
			if (current.getCause() == current) {
				break;
			}
			current = current.getCause();
		}
		return null;
	}

	private static JsonObject errorJson(String code, String message) {
		JsonObject json = new JsonObject();
		json.addProperty("status", "FAILED");
		json.addProperty("code", code);
		json.addProperty("message", message);
		return json;
	}

	private static void sendJson(HttpExchange exchange, int status, JsonObject json) throws IOException {
		byte[] bytes = GSON.toJson(json).getBytes(StandardCharsets.UTF_8);
		exchange.getResponseHeaders().set("Content-Type", "application/json; charset=utf-8");
		exchange.sendResponseHeaders(status, bytes.length);
		try (OutputStream out = exchange.getResponseBody()) {
			out.write(bytes);
		}
	}

	private void writeSessionFile() {
		JsonObject json = new JsonObject();
		json.addProperty("host", "127.0.0.1");
		json.addProperty("port", PORT);
		json.addProperty("token", token);
		json.addProperty("base_url", "http://127.0.0.1:" + PORT);
		String payload = GSON.toJson(json);
		MinecraftClient client = MinecraftClient.getInstance();
		try {
			Path gameFile = client.runDirectory.toPath().resolve("visual-probe").resolve("session.json");
			Files.createDirectories(gameFile.getParent());
			Files.writeString(gameFile, payload);
			VisualProbeClient.LOGGER.info("Wrote session file {}", gameFile.toAbsolutePath());
		} catch (IOException e) {
			VisualProbeClient.LOGGER.warn("Could not write game-dir session file", e);
		}
		try {
			Path tmp = Path.of(System.getProperty("java.io.tmpdir"), "mc-visual-probe-session.json");
			Files.writeString(tmp, payload);
			VisualProbeClient.LOGGER.info("Wrote session file {}", tmp.toAbsolutePath());
		} catch (IOException e) {
			VisualProbeClient.LOGGER.warn("Could not write temp session file", e);
		}
	}

	private static String generateToken() {
		byte[] bytes = new byte[24];
		new SecureRandom().nextBytes(bytes);
		return HexFormat.of().formatHex(bytes);
	}
}
