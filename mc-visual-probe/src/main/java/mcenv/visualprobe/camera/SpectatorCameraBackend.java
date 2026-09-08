package mcenv.visualprobe.camera;

import mcenv.visualprobe.api.ProbeException;
import net.minecraft.client.MinecraftClient;
import net.minecraft.client.network.ClientPlayerEntity;
import net.minecraft.client.render.Camera;
import net.minecraft.server.integrated.IntegratedServer;
import net.minecraft.server.network.ServerPlayerEntity;
import net.minecraft.server.world.ServerWorld;
import net.minecraft.util.math.Vec3d;
import net.minecraft.world.GameMode;

import java.util.Set;
import java.util.UUID;

/**
 * MVP-A camera backend: spectator-teleport the local player.
 * Gold-path CLIENT_CAMERA_ENTITY is deferred to Probe V0.3.
 */
public final class SpectatorCameraBackend implements CameraBackend {
	@Override
	public String id() {
		return "PLAYER_SPECTATOR";
	}

	@Override
	public void apply(MinecraftClient client, CameraPose pose) throws ProbeException {
		ClientPlayerEntity player = client.player;
		if (player == null) {
			throw ProbeException.noWorld();
		}
		IntegratedServer server = client.getServer();
		if (server != null) {
			UUID uuid = player.getUuid();
			server.execute(() -> teleportOnServer(server, uuid, pose));
			return;
		}
		if (client.player.networkHandler != null) {
			double feetY = pose.y() - player.getStandingEyeHeight();
			client.player.networkHandler.sendChatCommand(String.format(
				java.util.Locale.ROOT,
				"gamemode spectator"
			));
			client.player.networkHandler.sendChatCommand(String.format(
				java.util.Locale.ROOT,
				"tp @s %.4f %.4f %.4f %.4f %.4f",
				pose.x(),
				feetY,
				pose.z(),
				pose.yaw(),
				pose.pitch()
			));
			return;
		}
		throw ProbeException.backendUnavailable("No integrated server and no play network handler.");
	}

	@Override
	public CameraPose readback(MinecraftClient client, int fallbackFov) {
		Camera camera = client.gameRenderer.getCamera();
		Vec3d pos = camera.getCameraPos();
		int fov = fallbackFov;
		if (client.options != null) {
			fov = client.options.getFov().getValue();
		}
		return new CameraPose(pos.x, pos.y, pos.z, camera.getYaw(), camera.getPitch(), fov);
	}

	public void hold(MinecraftClient client, CameraPose pose) {
		ClientPlayerEntity player = client.player;
		if (player == null) {
			return;
		}
		player.setVelocity(Vec3d.ZERO);
		double feetY = pose.y() - player.getStandingEyeHeight();
		player.refreshPositionAndAngles(pose.x(), feetY, pose.z(), pose.yaw(), pose.pitch());
		player.setYaw(pose.yaw());
		player.setPitch(pose.pitch());
		player.setHeadYaw(pose.yaw());
		player.setBodyYaw(pose.yaw());
	}

	private static void teleportOnServer(IntegratedServer server, UUID uuid, CameraPose pose) {
		ServerPlayerEntity player = server.getPlayerManager().getPlayer(uuid);
		if (player == null) {
			return;
		}
		if (player.interactionManager.getGameMode() != GameMode.SPECTATOR) {
			player.changeGameMode(GameMode.SPECTATOR);
		}
		if (!(player.getEntityWorld() instanceof ServerWorld world)) {
			return;
		}
		double feetY = pose.y() - player.getStandingEyeHeight();
		player.teleport(world, pose.x(), feetY, pose.z(), Set.of(), pose.yaw(), pose.pitch(), false);
		player.setYaw(pose.yaw());
		player.setPitch(pose.pitch());
		player.setHeadYaw(pose.yaw());
		player.setBodyYaw(pose.yaw());
	}
}
