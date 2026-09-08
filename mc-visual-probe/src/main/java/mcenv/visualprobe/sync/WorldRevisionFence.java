package mcenv.visualprobe.sync;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import net.minecraft.block.BlockState;
import net.minecraft.client.world.ClientWorld;
import net.minecraft.registry.Registries;
import net.minecraft.util.math.BlockPos;

import java.util.ArrayList;
import java.util.List;

public final class WorldRevisionFence {
	public record Anchor(int x, int y, int z, String expectedBlock) {
	}

	private WorldRevisionFence() {
	}

	public static List<Anchor> parse(JsonObject request) {
		List<Anchor> anchors = new ArrayList<>();
		if (request == null || !request.has("sync_anchors") || !request.get("sync_anchors").isJsonArray()) {
			return anchors;
		}
		JsonArray array = request.getAsJsonArray("sync_anchors");
		for (JsonElement element : array) {
			if (!element.isJsonObject()) {
				continue;
			}
			JsonObject obj = element.getAsJsonObject();
			anchors.add(new Anchor(
				obj.get("x").getAsInt(),
				obj.get("y").getAsInt(),
				obj.get("z").getAsInt(),
				obj.get("expected_block").getAsString()
			));
		}
		return anchors;
	}

	public static String firstMismatch(ClientWorld world, List<Anchor> anchors) {
		for (Anchor anchor : anchors) {
			BlockPos pos = new BlockPos(anchor.x(), anchor.y(), anchor.z());
			BlockState state = world.getBlockState(pos);
			String actual = Registries.BLOCK.getId(state.getBlock()).toString();
			if (!actual.equals(anchor.expectedBlock())) {
				return "Anchor " + pos.toShortString() + " expected " + anchor.expectedBlock() + " but saw " + actual;
			}
		}
		return null;
	}
}
