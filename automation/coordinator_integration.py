"""Offline staged coordinator CLI. No sender, task execution or runtime activation."""
import argparse
import json
from pathlib import Path
import time

from automation import coordinator as c
from automation import coordinator_outbox as outbox
from automation.coordinator_io import decode, read_bytes
from automation.coordinator_parent import export_parent
from automation.coordinator_sources import observations, FAILURES


def public_projection(output):
    """Fixed summary only; no payload, paths, destinations or imported prose."""
    report = output.get('report') or {}
    return {'changed': output.get('changed', False),
            'material_change_pending': output.get('material_change_pending', False),
            'backpressure': output.get('backpressure', False),
            'reason': output.get('reason', 'prepared' if output.get('changed') else 'unchanged'),
            'sources': {k: {'status': v['status'], 'reason': v['reason']}
                        for k, v in report.get('sources', {}).items()},
            'pending_reports': [{'id': item['id'], 'sha256': item['sha256'],
                                 'publication': item['publication']['status'],
                                 'recipient_delivery': item['recipient_delivery']}
                                for item in output.get('pending_outbox', [])]}


def recover(path, report_id, output):
    """Export the exact immutable bytes for the existing publication owner."""
    import os
    import tempfile
    for item in outbox.view(path):
        if item['id'] != report_id:
            continue
        output = Path(output)
        checkout = Path(__file__).resolve().parent.parent
        c.require(output.parent.is_dir() and not output.is_symlink()
                  and checkout != output.resolve() and checkout not in output.resolve().parents, 'report_output')
        content = item['payload'].encode()
        # Never overwrite divergent bytes, even for a local recovery command.
        if output.exists():
            c.require(read_bytes(output.parent, output.name, outbox.MAX_PAYLOAD) == content, 'report_output_conflict')
            return item['sha256']
        fd, name = tempfile.mkstemp(prefix='.report-', dir=output.parent)
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(content); stream.flush(); os.fsync(stream.fileno())
            # Create-only link gives a racing destination the same conflict check.
            os.link(name, output)
            directory = os.open(output.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            os.unlink(name)
        return item['sha256']
    raise ValueError('unknown_report')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    stage = sub.add_parser('report')
    stage.add_argument('--root', required=True, type=Path)
    stage.add_argument('--manifest', default='manifest.json')
    stage.add_argument('--state', required=True, type=Path)
    stage.add_argument('--intent', type=Path)
    parent = sub.add_parser('parent-export')
    parent.add_argument('--root', required=True, type=Path)
    parent.add_argument('--issue', required=True, type=int)
    parent.add_argument('--task', required=True, action='append', type=int)
    parent.add_argument('--output', required=True, type=Path)
    for command in ('pending', 'recover', 'publication-uncertain', 'receipt'):
        item = sub.add_parser(command)
        item.add_argument('--state', required=True, type=Path)
        if command != 'pending':
            item.add_argument('--id', required=True)
        if command == 'recover':
            item.add_argument('--output', required=True, type=Path)
        if command == 'receipt':
            item.add_argument('--worker-root', required=True, type=Path)
            item.add_argument('--issue', required=True, type=int)
            item.add_argument('--task', required=True, type=int)
            item.add_argument('--trusted-receipt-sha256', required=True)
            item.add_argument('--artifact-root', required=True, type=Path)
            item.add_argument('--artifact-file', required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == 'report':
            intent = (decode(read_bytes(args.intent.parent, args.intent.name)) if args.intent else None)
            result = public_projection(outbox.poll(args.state,
                lambda: observations(args.root, args.manifest, time.time()), intent))
        elif args.command == 'parent-export':
            value = export_parent(args.root, args.issue, args.task, time.time())
            c.atomic_save(args.output, value)
            result = {'status': value['status'], 'reason': value['reason'], 'writer_liveness': 'unknown'}
        elif args.command == 'recover':
            result = {'sha256': recover(args.state, args.id, args.output), 'status': 'recovered'}
        else:
            if args.command == 'receipt':
                pending = outbox.reconcile_publication(args.state, args.id, args.worker_root,
                    args.issue, args.task, args.trusted_receipt_sha256, args.artifact_root, args.artifact_file)
            elif args.command == 'publication-uncertain':
                pending = outbox.publication_uncertain(args.state, args.id)
            else:
                pending = outbox.view(args.state)
            result = public_projection({'pending_outbox': pending})
        print(json.dumps(result, sort_keys=True))
        return 0
    except FAILURES:
        print(json.dumps({'state': 'NEEDS_USER', 'reason': 'invalid_or_unavailable_input'}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
