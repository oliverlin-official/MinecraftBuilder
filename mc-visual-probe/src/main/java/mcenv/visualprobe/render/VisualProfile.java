package mcenv.visualprobe.render;

import net.minecraft.client.MinecraftClient;
import net.minecraft.client.option.Perspective;
import net.minecraft.client.option.SimpleOption;

public final class VisualProfile {
	public enum Id {
		DEBUG,
		PRODUCTION,
		SHOWCASE
	}

	public record Applied(
		boolean previousHudHidden,
		int previousFov,
		Perspective previousPerspective,
		boolean previousPauseOnLostFocus
	) {
	}

	private VisualProfile() {
	}

	public static Id parse(String raw) {
		if (raw == null || raw.isBlank()) {
			return Id.PRODUCTION;
		}
		return Id.valueOf(raw.trim().toUpperCase());
	}

	public static Applied apply(MinecraftClient client, Id profile, int fov, boolean hideHud) {
		SimpleOption<Integer> fovOption = client.options.getFov();
		int previousFov = fovOption.getValue();
		boolean previousHud = client.options.hudHidden;
		Perspective previousPerspective = client.options.getPerspective();
		boolean previousPauseOnLostFocus = client.options.pauseOnLostFocus;

		int clamped = Math.max(30, Math.min(110, fov));
		fovOption.setValue(clamped);
		if (hideHud || profile != Id.DEBUG) {
			client.options.hudHidden = true;
		}
		client.options.setPerspective(Perspective.FIRST_PERSON);
		client.options.pauseOnLostFocus = false;
		dismissOverlay(client);
		return new Applied(previousHud, previousFov, previousPerspective, previousPauseOnLostFocus);
	}

	public static void dismissOverlay(MinecraftClient client) {
		if (client.currentScreen != null) {
			client.setScreen(null);
		}
	}

	public static boolean worldViewReady(MinecraftClient client) {
		dismissOverlay(client);
		return client.currentScreen == null && !client.isPaused();
	}

	public static void restore(MinecraftClient client, Applied applied) {
		if (applied == null || client.options == null) {
			return;
		}
		client.options.getFov().setValue(applied.previousFov());
		client.options.hudHidden = applied.previousHudHidden();
		client.options.setPerspective(applied.previousPerspective());
		client.options.pauseOnLostFocus = applied.previousPauseOnLostFocus();
	}
}
