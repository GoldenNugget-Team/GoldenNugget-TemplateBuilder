"""Start Batter Builder (also the entry point for the packaged app)."""
import sys

if __name__ == "__main__":
    if sys.argv[1:] == ["--smoke"]:
        from batter_builder.smoke import run
        sys.exit(run())
    from batter_builder.ui.app import main
    main()
