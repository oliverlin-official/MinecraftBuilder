package mcenv.visualprobe.camera;

import mcenv.visualprobe.api.ProbeException;
import net.minecraft.client.MinecraftClient;

public interface CameraBackend {
	String id();

	void apply(MinecraftClient client, CameraPose pose) throws ProbeException;

	CameraPose readback(MinecraftClient client, int fallbackFov);
}
