# -*- mode: python ; coding: utf-8 -*-
"""
StealthReader 打包配置

解决的问题：
  onefile EXE 运行时弹窗报：
  Failed to extract api-ms-win-core-kernel32-legacy-l1-1-1.dll:
  decompression resulted in return code -1!

根因：
  PyInstaller 在 Windows runner 上把系统 API Set 转发 DLL（api-ms-win-* /
  ext-ms-win-*）一起收进了归档（实测 40+ 个）。这些 DLL 是 Windows 用
  ApiSetSchema 自己解析的虚拟 DLL，本来就不该打包，捆进去有两个害处：
    1) 部分 Windows 版本上读到的字节数与归档声明不符 → 解压返回 -1（本次报错）
    2) 往临时目录释放 api-ms-win-*.dll 是典型的 DLL 劫持/释放型木马特征，
       极易触发杀软实时防护拦截（拦截同样表现为解压失败）
  所以这里在 Analysis 之后把它们从 binaries 里过滤掉。

用法：
  pyinstaller --clean --noconfirm StealthReader.spec           # 单文件版（默认）
  SR_MODE=onedir pyinstaller --noconfirm StealthReader.spec    # 目录版（兜底，不解压临时文件）
"""
import os

from PyInstaller.utils.hooks import collect_submodules

MODE = os.environ.get('SR_MODE', 'onefile').strip().lower()
ONEDIR = MODE == 'onedir'

# Windows 自带的 API Set 转发 DLL 前缀，一律不打包
API_SET_PREFIXES = ('api-ms-win-', 'ext-ms-win-')

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    # keyboard 包在运行时按平台动态导入 _winkeyboard 等子模块，静态分析抓不全
    hiddenimports=collect_submodules('keyboard'),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'unittest', 'pydoc', 'doctest', 'test'],
    noarchive=False,
)

_before = len(a.binaries)
a.binaries = [b for b in a.binaries if not b[0].lower().startswith(API_SET_PREFIXES)]
_DROPPED = [b[0] for b in a.binaries if b[0].lower().startswith(API_SET_PREFIXES)]
print('[spec] binaries: %d -> %d (丢弃 %d 个 API Set DLL)'
      % (_before, len(a.binaries), _before - len(a.binaries)))
if _DROPPED:
    print('[spec] !! 仍有残留:', _DROPPED)

pyz = PYZ(a.pure)

_common = dict(
    name='StealthReader',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,                      # 不加壳，减少杀软启发式误报
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='read.ico',
    version='version_info.txt',     # 带版本资源，降低"未知发布者"观感
)

if ONEDIR:
    exe = EXE(pyz, a.scripts, [], exclude_binaries=True, **_common)
    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=False,
        upx_exclude=[],
        name='StealthReader',
    )
else:
    exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], **_common)
