package mcenv.visualprobe.render;

import net.minecraft.client.world.ClientWorld;
import net.minecraft.util.math.BlockPos;
import net.minecraft.util.math.ChunkPos;
import net.minecraft.world.chunk.ChunkStatus;
import net.minecraft.world.chunk.WorldChunk;

public final class ChunkReadiness {
	private ChunkReadiness() {
	}

	public static int loadedRadius(ClientWorld world, double x, double z, int required) {
		ChunkPos origin = new ChunkPos(BlockPos.ofFloored(x, 0, z));
		int best = -1;
		for (int r = 0; r <= required; r++) {
			if (!ringLoaded(world, origin, r)) {
				return best;
			}
			best = r;
		}
		return best;
	}

	public static boolean ready(ClientWorld world, double x, double z, int required) {
		return loadedRadius(world, x, z, required) >= required;
	}

	private static boolean ringLoaded(ClientWorld world, ChunkPos origin, int radius) {
		for (int dx = -radius; dx <= radius; dx++) {
			for (int dz = -radius; dz <= radius; dz++) {
				if (Math.max(Math.abs(dx), Math.abs(dz)) != radius) {
					continue;
				}
				WorldChunk chunk = world.getChunkManager().getChunk(
					origin.x + dx,
					origin.z + dz,
					ChunkStatus.FULL,
					false
				);
				if (chunk == null) {
					return false;
				}
			}
		}
		return true;
	}
}
