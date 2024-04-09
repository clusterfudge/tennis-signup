import sys
from datetime import timedelta

from storage import Storage

CLEANUP_SPEC = {
    'plan': timedelta(days=90),
    'sched': timedelta(days=90),
    'cal_event': timedelta(days=90),
    'http': timedelta(days=14)
}


def main(args=sys.argv):
    dry_run = '--dry-run=false' in args
    s = Storage('./storage')
    log_storage = Storage('./log')

    for t, window in CLEANUP_SPEC.items():
        cleaned = s.cleanup(t, retention_window=window, dry_run=dry_run)
        cleaned += log_storage.cleanup(t, retention_window=window, dry_run=dry_run)
        if len(cleaned) > 0:
            print(f"DRY_RUN={dry_run}: cleaned {len(cleaned)} items from {t}.")


if __name__ == "__main__":
    main()
