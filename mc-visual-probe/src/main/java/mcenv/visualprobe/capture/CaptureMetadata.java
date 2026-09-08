package mcenv.visualprobe.capture;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import mcenv.visualprobe.camera.CameraPose;
import mcenv.visualprobe.render.VisualProfile;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;

public record CaptureMetadata(
	String captureId,
	String observationId,
	int worldRevision,
	CameraPose camera,
	String renderProfile,
	int[] resolution,
	int viewDistance,
	boolean hudHidden,
	String dimension,
	long timeOfDay,
	String weather,
	String timestamp,
	String minecraftVersion,
	String cameraBackend,
	String pngPath
) {
	private static final Gson GSON = new GsonBuilder().setPrettyPrinting().create();

	public JsonObject toJson() {
		JsonObject json = new JsonObject();
		json.addProperty("capture_id", captureId);
		json.addProperty("observation_id", observationId);
		json.addProperty("world_revision", worldRevision);
		json.addProperty("world_version", worldRevision);
		json.add("camera", camera.toJson());
		json.addProperty("x", camera.x());
		json.addProperty("y", camera.y());
		json.addProperty("z", camera.z());
		json.addProperty("yaw", camera.yaw());
		json.addProperty("pitch", camera.pitch());
		json.addProperty("roll", 0.0);
		json.addProperty("fov", camera.fov());
		JsonObject render = new JsonObject();
		render.addProperty("profile", renderProfile);
		JsonArray res = new JsonArray();
		res.add(resolution[0]);
		res.add(resolution[1]);
		render.add("resolution", res);
		render.addProperty("view_distance", viewDistance);
		render.addProperty("hud_hidden", hudHidden);
		json.add("render", render);
		json.add("resolution", res);
		JsonObject environment = new JsonObject();
		environment.addProperty("dimension", dimension);
		environment.addProperty("time", timeOfDay);
		environment.addProperty("weather", weather);
		json.add("environment", environment);
		json.addProperty("dimension", dimension);
		json.addProperty("timestamp", timestamp);
		json.addProperty("minecraft_version", minecraftVersion);
		json.addProperty("camera_backend", cameraBackend);
		json.addProperty("file", pngPath);
		json.addProperty("render_profile", renderProfile);
		return json;
	}

	public void write(Path path) throws IOException {
		Files.createDirectories(path.getParent());
		Files.writeString(path, GSON.toJson(toJson()));
	}

	public static VisualProfile.Id profileOrDefault(String raw) {
		return VisualProfile.parse(raw);
	}
}
