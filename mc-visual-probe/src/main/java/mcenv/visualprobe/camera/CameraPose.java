package mcenv.visualprobe.camera;

import com.google.gson.JsonObject;
import net.minecraft.util.math.MathHelper;

public record CameraPose(double x, double y, double z, float yaw, float pitch, int fov) {
	public static CameraPose fromJson(JsonObject json) {
		JsonObject pose = json.has("pose") && json.get("pose").isJsonObject()
			? json.getAsJsonObject("pose")
			: json;
		JsonObject position = pose.has("position") && pose.get("position").isJsonObject()
			? pose.getAsJsonObject("position")
			: pose;
		JsonObject rotation = pose.has("rotation") && pose.get("rotation").isJsonObject()
			? pose.getAsJsonObject("rotation")
			: pose;
		if (!position.has("x") || !position.has("y") || !position.has("z")) {
			throw new IllegalArgumentException("Pose requires x, y, z.");
		}
		if (!rotation.has("yaw") || !rotation.has("pitch")) {
			throw new IllegalArgumentException("Pose requires yaw and pitch.");
		}
		int fov = 70;
		if (pose.has("fov")) {
			fov = pose.get("fov").getAsInt();
		} else if (json.has("fov")) {
			fov = json.get("fov").getAsInt();
		}
		return new CameraPose(
			position.get("x").getAsDouble(),
			position.get("y").getAsDouble(),
			position.get("z").getAsDouble(),
			rotation.get("yaw").getAsFloat(),
			rotation.get("pitch").getAsFloat(),
			fov
		);
	}

	public JsonObject toJson() {
		JsonObject json = new JsonObject();
		json.addProperty("x", x);
		json.addProperty("y", y);
		json.addProperty("z", z);
		json.addProperty("yaw", yaw);
		json.addProperty("pitch", pitch);
		json.addProperty("fov", fov);
		return json;
	}

	public boolean matches(CameraPose other, double posEpsilon, float rotEpsilon) {
		if (other == null) {
			return false;
		}
		return Math.abs(x - other.x) <= posEpsilon
			&& Math.abs(y - other.y) <= posEpsilon
			&& Math.abs(z - other.z) <= posEpsilon
			&& Math.abs(MathHelper.wrapDegrees(yaw - other.yaw)) <= rotEpsilon
			&& Math.abs(MathHelper.wrapDegrees(pitch - other.pitch)) <= rotEpsilon
			&& fov == other.fov;
	}

	public CameraPose withFov(int newFov) {
		return new CameraPose(x, y, z, yaw, pitch, newFov);
	}
}
