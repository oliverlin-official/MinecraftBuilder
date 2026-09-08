package mcenv.visualprobe.capture;

import mcenv.visualprobe.VisualProbeClient;
import mcenv.visualprobe.api.ProbeException;
import net.minecraft.client.MinecraftClient;
import net.minecraft.client.gl.Framebuffer;
import net.minecraft.client.texture.NativeImage;
import net.minecraft.client.util.ScreenshotRecorder;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.concurrent.CompletableFuture;

public final class ScreenshotService {
	public record Result(Path path, int width, int height) {
	}

	public CompletableFuture<Result> capture(MinecraftClient client, Path pngPath) {
		CompletableFuture<Result> future = new CompletableFuture<>();
		Framebuffer framebuffer = client.getFramebuffer();
		if (framebuffer == null) {
			future.completeExceptionally(ProbeException.framebufferUnavailable());
			return future;
		}
		try {
			Files.createDirectories(pngPath.getParent());
		} catch (IOException e) {
			future.completeExceptionally(ProbeException.screenshotFailed("Could not create screenshot directory: " + e.getMessage()));
			return future;
		}
		try {
			ScreenshotRecorder.takeScreenshot(framebuffer, image -> finishWrite(image, pngPath, future));
		} catch (RuntimeException e) {
			future.completeExceptionally(ProbeException.screenshotFailed(e.getMessage()));
		}
		return future;
	}

	private static void finishWrite(NativeImage image, Path pngPath, CompletableFuture<Result> future) {
		try {
			image.writeTo(pngPath.toFile());
			future.complete(new Result(pngPath, image.getWidth(), image.getHeight()));
		} catch (Exception e) {
			future.completeExceptionally(ProbeException.screenshotFailed(e.getMessage()));
		} finally {
			image.close();
			VisualProbeClient.LOGGER.info("Wrote screenshot {}", pngPath.toAbsolutePath());
		}
	}
}
