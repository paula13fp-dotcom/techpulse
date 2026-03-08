"""TechPulse — entry point."""
import sys
from techpulse.database.connection import init_db
from techpulse.scheduler.job_manager import start_scheduler, stop_scheduler, trigger_now
from techpulse.ui.app import create_app
from techpulse.ui.main_window import MainWindow


def main():
    # Initialize database
    init_db()

    # Start background scheduler
    start_scheduler()

    # Trigger an initial scrape on first run if DB is empty
    from techpulse.database.queries import get_post_count
    if get_post_count() == 0:
        trigger_now()

    # Launch UI
    app = create_app(sys.argv)
    window = MainWindow()
    window.show()

    exit_code = app.exec()
    stop_scheduler()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
