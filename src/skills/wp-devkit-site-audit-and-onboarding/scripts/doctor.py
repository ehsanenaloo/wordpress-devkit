"""Read-only filesystem/tool inventory; trusted WordPress bootstrap is explicit opt-in."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import tempfile
import sys

# Installed skill resources must remain immutable after execution.
sys.dont_write_bytecode = True
from evidence_report import new_report, write_report

COLLECTOR = r'''
define('DISABLE_WP_CRON', true);
ob_start();
require $argv[1] . '/wp-load.php';
require_once ABSPATH . 'wp-admin/includes/plugin.php';
$plugins = [];
foreach (get_plugins() as $file => $data) {
    $plugins[] = ['file' => $file, 'version' => $data['Version'],
        'active' => is_plugin_active($file), 'network_active' => is_plugin_active_for_network($file)];
}
$hpos = class_exists('Automattic\\WooCommerce\\Utilities\\OrderUtil')
    ? Automattic\WooCommerce\Utilities\OrderUtil::custom_orders_table_usage_is_enabled() : null;
$result = ['wordpress' => get_bloginfo('version'), 'php' => PHP_VERSION,
    'multisite' => is_multisite(), 'external_object_cache' => wp_using_ext_object_cache(),
    'woocommerce' => defined('WC_VERSION') ? WC_VERSION : null, 'hpos' => $hpos,
    'theme' => ['stylesheet' => get_stylesheet(), 'version' => wp_get_theme()->get('Version')],
    'plugins' => $plugins];
ob_end_clean();
echo json_encode($result, JSON_THROW_ON_ERROR);
'''


def safe_which(name, untrusted=()):
    """Find an executable on PATH without ever choosing one that lives in the inspected project.

    On Windows shutil.which searches the current directory first, so a node.cmd or php.bat inside an
    untrusted checkout would otherwise be executed by the version probes.
    """
    os.environ['NoDefaultCurrentDirectoryInExePath'] = '1'
    blocked = [Path(item).resolve() for item in (Path.cwd(), *untrusted)]
    search = os.pathsep.join(entry for entry in os.environ.get('PATH', '').split(os.pathsep)
                             if entry and Path(entry).resolve() not in blocked
                             and not any(parent in blocked for parent in Path(entry).resolve().parents))
    return shutil.which(name, path=search)


def kill_tree(process):
    """Stop a timed-out probe together with the processes it started (npm.cmd starts node)."""
    if os.name == 'nt':
        subprocess.run(['taskkill', '/T', '/F', '/PID', str(process.pid)], capture_output=True, check=False)
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except OSError:
            pass
    process.kill()


def probe(arguments, timeout=15):
    # Run from a neutral directory so project-level shims and configuration are not picked up.
    options = {} if os.name == 'nt' else {'start_new_session': True}
    try:
        process = subprocess.Popen(arguments, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                   encoding='utf-8', errors='replace', cwd=tempfile.gettempdir(), **options)
    except OSError:
        return None
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        kill_tree(process)
        try:
            process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            pass
        return None
    return subprocess.CompletedProcess(arguments, process.returncode, stdout, stderr)


def validate_runtime(data):
    if not isinstance(data, dict) or set(data) != {'wordpress', 'php', 'multisite',
            'external_object_cache', 'woocommerce', 'hpos', 'theme', 'plugins'}:
        raise ValueError('Unexpected collector output.')
    version = lambda value: isinstance(value, str) and bool(re.fullmatch(r'[0-9]+(?:\.[0-9]+){1,3}(?:[-+][A-Za-z0-9.-]+)?', value))
    if not all(version(data[key]) for key in ('wordpress', 'php')):
        raise ValueError('Invalid runtime versions.')
    if data['woocommerce'] is not None and not version(data['woocommerce']):
        raise ValueError('Invalid WooCommerce version.')
    if any(type(data[key]) is not bool for key in ('multisite', 'external_object_cache')):
        raise ValueError('Invalid runtime flags.')
    if data['hpos'] is not None and type(data['hpos']) is not bool:
        raise ValueError('Invalid HPOS flag.')
    theme = data['theme']
    if not isinstance(theme, dict) or set(theme) != {'stylesheet', 'version'} or not isinstance(theme['stylesheet'], str) or not re.fullmatch(r'[A-Za-z0-9_./-]+', theme['stylesheet']) or not isinstance(theme['version'], str) or len(theme['version']) > 128 or any(ord(char) < 32 for char in theme['version']):
        raise ValueError('Invalid theme metadata.')
    if not isinstance(data['plugins'], list) or len(data['plugins']) > 2000:
        raise ValueError('Invalid plugin inventory.')
    for plugin in data['plugins']:
        if not isinstance(plugin, dict) or set(plugin) != {'file', 'version', 'active', 'network_active'}:
            raise ValueError('Invalid plugin metadata.')
        # The Version header is free text (for example "3", "2024.1", "v1.2" or "1.0 beta"); accept
        # any bounded printable string, as for themes, so one unusual header cannot discard the inventory.
        text = plugin['version']
        if not isinstance(plugin['file'], str) or not re.fullmatch(r'[A-Za-z0-9_./-]+\.php', plugin['file']) or not isinstance(text, str) or len(text) > 128 or any(ord(char) < 32 for char in text):
            raise ValueError('Invalid plugin identity/version.')
        if any(type(plugin[key]) is not bool for key in ('active', 'network_active')):
            raise ValueError('Invalid plugin activation flags.')
    return data


def inventory(target, container=None, trusted_runtime=False, wordpress_root='/var/www/html', redact_paths=False):
    target = Path(target).resolve(strict=True)
    if not target.is_dir():
        raise ValueError('Target must be a directory.')
    if container and not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}', container):
        raise ValueError('Invalid container name.')
    if trusted_runtime and not container:
        raise ValueError('Trusted runtime requires an explicitly selected container.')
    if not re.fullmatch(r'/[A-Za-z0-9_./-]+', wordpress_root) or '..' in Path(wordpress_root).parts:
        raise ValueError('WordPress container root must be an absolute normalized path.')
    label = (target.name or 'root') if redact_paths else str(target)
    report = new_report('directory:' + label + (';container:' + container
                        + ';wordpress-root:' + wordpress_root if container else ''))

    def check(identifier, status, message, evidence=None):
        report['checks'].append({'id': identifier, 'status': status, 'message': message,
                                 'evidence': evidence or {}})

    signals = [name for name in ('composer.json', 'package.json', 'wp-config.php',
               'wp-content', 'web/wp', 'theme.json', 'block.json', 'docker-compose.yml',
               'compose.yaml', 'compose.yml') if (target / name).exists()]
    check('filesystem', 'passed', 'Top-level layout inspected without evaluating project code.', {'signals': signals})
    # Do not read wp-config.php, .env, composer scripts, plugin code or Docker environment.
    tools = {'php': ['--version'], 'node': ['--version'], 'npm': ['--version'],
             'python': ['--version'], 'docker': ['--version'], 'wp': ['--version']}
    for name, flags in tools.items():
        executable = safe_which(name + '.cmd' if name == 'npm' and safe_which('npm.cmd', (target,)) else name, (target,))
        if executable is None:
            check('tool:' + name, 'unavailable', 'Executable is not available on PATH.')
            continue
        # WP-CLI may execute project wp-cli.yml require hooks, so never launch it here.
        if name == 'wp':
            check('tool:wp', 'skipped', 'WP-CLI found; version execution omitted to avoid project bootstrap.')
            continue
        result = probe([executable, *flags])
        if result is None:
            check('tool:' + name, 'failed', 'Version probe could not finish within the time limit.')
        elif result.returncode:
            # A broken shim (Microsoft Store python stub, nvm without a selected version) is not a doctor failure.
            check('tool:' + name, 'unavailable', 'Executable is present but its version probe returned an error.',
                  {'exit_code': result.returncode})
        else:
            # Allowlist version lines; never forward arbitrary command diagnostics.
            version = re.search(r'(?<![\w.])v?(\d+\.\d+(?:\.\d+)?(?:[-+][A-Za-z0-9.-]+)?)', result.stdout)
            check('tool:' + name, 'passed' if version else 'unavailable',
                  'Version detected.' if version else 'Version output was not recognized.',
                  {'version': version.group(1)} if version else {})
    if container:
        executable = safe_which('docker', (target,))
        result = probe([executable, 'inspect', '--format', '{{json .State.Running}}', container]) if executable else None
        running = result is not None and result.returncode == 0 and result.stdout.strip() == 'true'
        check('docker:container', 'passed' if running else 'unavailable',
              'Selected container is running.' if running else 'Selected container could not be inspected.')
        if trusted_runtime and running:
            result = probe([executable, 'exec', container, 'php', '-r', COLLECTOR, wordpress_root], timeout=30)
            try:
                data = json.loads(result.stdout) if result is not None and result.returncode == 0 else None
                validate_runtime(data)
            except (ValueError, TypeError):
                check('wordpress:runtime', 'failed', 'Runtime collector failed; diagnostics were withheld to protect secrets.')
            else:
                check('wordpress:runtime', 'passed', 'Selected trusted runtime inventory collected.', data)
        else:
            check('wordpress:runtime', 'skipped', 'Runtime bootstrap was not performed.')
    else:
        check('wordpress:runtime', 'skipped', 'No runtime container selected.')
    report['limits'] = ['Inventory is not a vulnerability scan or compatibility certification.',
        'Filesystem mode does not discover active plugins, HPOS or runtime cache state.',
        'Trusted runtime executes WordPress and active plugin bootstrap; those may have side effects despite the collector making no maintenance writes.',
        'No credentials, environment values, database contents or arbitrary process diagnostics are collected.']
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('target', nargs='?', default='.')
    parser.add_argument('--container')
    parser.add_argument('--trusted-runtime', action='store_true')
    parser.add_argument('--wordpress-root', default='/var/www/html')
    parser.add_argument('--redact-paths', action='store_true',
                        help='record only the directory name of the target, not its absolute path')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        report = inventory(args.target, args.container, args.trusted_runtime, args.wordpress_root, args.redact_paths)
        # Keep generated evidence outside the inspected source directory.
        destination = args.output.resolve()
        target_path = Path(args.target).resolve()
        if destination == target_path or target_path in destination.parents:
            raise ValueError('Report output must be outside the inspected target directory.')
        write_report(report, destination)
    except (ValueError, OSError) as error:
        parser.error(str(error))
    print('Doctor report written: ' + str(destination / 'report.html'))
    return int(any(check['status'] == 'failed' for check in report['checks']))


if __name__ == '__main__':
    raise SystemExit(main())
