import reflex as rx

config = rx.Config(
	app_name="codoc_in_md",
	# Reflex 0.10 has no default database (0.8 used this file); DocumentModel lives here.
	db_url="sqlite:///reflex.db",
	plugins=[
		# Always light (moved here from rx.App(theme=...), which Reflex deprecated).
		rx.plugins.RadixThemesPlugin(theme=rx.theme(appearance="light")),
		rx.plugins.TailwindV3Plugin(
			config={
				"plugins": ["@tailwindcss/typography@0.5.20"],
				# Reflex 0.10 compiles memoized components (e.g. the markdown preview)
				# into .web/app_components, which the plugin's default content globs
				# miss, so their classes would never be generated.
				"content": [
					"./app/**/*.{js,ts,jsx,tsx}",
					"./utils/**/*.{js,ts,jsx,tsx}",
					"./app_components/**/*.{js,ts,jsx,tsx}",
				],
			},
		),
	],
	disable_plugins=[rx.plugins.SitemapPlugin],
)
