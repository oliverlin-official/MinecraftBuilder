package mcenv.visualprobe;

import mcenv.visualprobe.api.LocalHttpServer;
import mcenv.visualprobe.camera.SpectatorCameraBackend;
import mcenv.visualprobe.capture.ScreenshotService;
import mcenv.visualprobe.observe.ObserveEngine;
import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientLifecycleEvents;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.fabricmc.fabric.api.client.networking.v1.ClientPlayConnectionEvents;
import net.minecraft.client.MinecraftClient;
import net.minecraft.text.Text;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public final class VisualProbeClient implements ClientModInitializer {
	public static final String MOD_ID = "mc-visual-probe";
	public static final Logger LOGGER = LoggerFactory.getLogger(MOD_ID);

	private static VisualProbeClient instance;

	private ObserveEngine engine;
	private LocalHttpServer httpServer;

	public static VisualProbeClient getInstance() {
		return instance;
	}

	public ObserveEngine engine() {
		return engine;
	}

	@Override
	public void onInitializeClient() {
		instance = this;
		engine = new ObserveEngine(new SpectatorCameraBackend(), new ScreenshotService());
		httpServer = new LocalHttpServer(engine);
		httpServer.start();

		ClientTickEvents.END_CLIENT_TICK.register(engine::tick);
		ClientPlayConnectionEvents.JOIN.register((handler, sender, client) ->
			client.execute(() -> notifyReady(client)));
		ClientLifecycleEvents.CLIENT_STOPPING.register(client -> {
			if (httpServer != null) {
				httpServer.stop();
			}
		});
		LOGGER.info("mc-visual-probe client initialized");
	}

	private static void notifyReady(MinecraftClient client) {
		if (client.inGameHud == null) {
			return;
		}
		client.inGameHud.getChatHud().addMessage(
			Text.literal("Visual Probe listening on http://127.0.0.1:" + LocalHttpServer.PORT)
		);
	}
}
