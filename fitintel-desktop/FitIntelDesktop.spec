# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from PyInstaller.utils.hooks import collect_submodules

BASE = os.path.abspath(SPECPATH)                    # ...\fitintel-desktop
ROOT = os.path.abspath(os.path.join(BASE, '..'))    # корень репо

# Делаем пакет `windows` видимым для PyInstaller
if BASE not in sys.path:
    sys.path.insert(0, BASE)

hiddenimports = ['PyQt6.sip', 'cv2', 'smartcard']
hiddenimports += collect_submodules('cv2')
hiddenimports += collect_submodules('smartcard')
hiddenimports += collect_submodules('PyQt6.QtMultimedia')
# Явный список всех модулей windows — collect_submodules('windows')
# не срабатывает из-за pathex, поэтому перечисляем вручную
hiddenimports += [
    'windows.aa_integration_tab',
    'windows.accounting_tab',
    'windows.activation_dialog',
    'windows.ai_center_tab',
    'windows.ai_hub_tab',
    'windows.analytics_tab',
    'windows.audit_tab',
    'windows.bank_settings_tab',
    'windows.change_password_dialog',
    'windows.change_password_self_dialog',
    'windows.chart_widget',
    'windows.clients_tab',
    'windows.clock_board',
    'windows.club_params_tab',
    'windows.commerce_tab',
    'windows.connections_tab',
    'windows.connectors_tab',
    'windows.credentials_tab',
    'windows.dashboard_tab',
    'windows.devices_tab',
    'windows.documents_tab',
    'windows.export_tab',
    'windows.face_id_tab',
    'windows.finance_hub_tab',
    'windows.form_dialog',
    'windows.help_dialog',
    'windows.hub_base',
    'windows.integrations_tab',
    'windows.license_tab',
    'windows.login_window',
    'windows.main_window',
    'windows.messenger_tab',
    'windows.music_tab',
    'windows.notifications_tab',
    'windows.payments_tab',
    'windows.print_helper',
    'windows.reports_tab',
    'windows.roles_tab',
    'windows.schedule_tab',
    'windows.services_settings_tab',
    'windows.services_tab',
    'windows.settings_hub_tab',
    'windows.settings_tab',
    'windows.setup_tab',
    'windows.shop_tab',
    'windows.startup_dialog',
    'windows.subscriptions_tab',
    'windows.tariffs_tab',
    'windows.theme',
    'windows.ui_config_tab',
    'windows.users_tab',
    'windows.visits_tab',
]

datas = [
    (os.path.join(ROOT, 'mpv', 'mpv.exe'),             'mpv'),
    (os.path.join(ROOT, 'mpv', 'mpv.com'),             'mpv'),
    (os.path.join(ROOT, 'mpv', 'd3dcompiler_43.dll'),  'mpv'),
    (os.path.join(ROOT, 'tools', 'nssm.exe'),          'tools'),
    (os.path.join(ROOT, 'scripts', 'music'),           'scripts/music'),
    (os.path.join(BASE, 'assets'),                     'assets'),
]

a = Analysis(
    [os.path.join(BASE, 'main.py')],
    pathex=[BASE, os.path.join(BASE, 'windows')],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='FitIntelDesktop',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=[os.path.join(BASE, 'assets', 'FitIntel_icon.ico')],
)