#!/usr/bin/env python

"""Ninja toolchain abstraction for Clang compiler suite"""

import os

import toolchain

class ClangToolchain(toolchain.Toolchain):

  def initialize(self, project, archs, configs, includepaths, dependlibs, libpaths, variables):
    #Local variable defaults
    self.toolchain = ''
    self.includepaths = includepaths
    self.libpaths = libpaths
    self.ccompiler = 'clang'
    self.archiver = 'llvm-ar'
    self.linker = 'clang'

    #Command definitions
    self.cccmd = '$toolchain$cc -MMD -MT $out -MF $out.d -I. $includepaths $moreincludepaths $cflags $carchflags $cconfigflags -c $in -o $out'
    self.ccdeps = 'gcc'
    self.ccdepfile = '$out.d'
    self.arcmd = self.rmcmd('$out') + ' && $toolchain$ar crsD $ararchflags $arflags $out $in'
    self.linkcmd = '$toolchain$cc $libpaths $configlibpaths $linkflags $linkarchflags $linkconfigflags -o $out $in $libs $archlibs $oslibs'

    #Base flags
    self.cflags = [ '-std=c11', '-D' + project.upper() + '_COMPILE=1',
                    '-W', '-Werror', '-pedantic', '-Wall', '-Weverything',
                    '-Wno-padded', '-Wno-documentation-unknown-command',
                    '-funit-at-a-time', '-fstrict-aliasing',
                    '-fno-math-errno','-ffinite-math-only', '-funsafe-math-optimizations',
                    '-fno-trapping-math', '-ffast-math' ]
    self.mflags = []
    self.arflags = []
    self.linkflags = []
    self.oslibs = []

    if self.is_monolithic():
      self.cflags += ['-DBUILD_MONOLITHIC=1']

    self.initialize_archs(archs)
    self.initialize_configs(configs)
    self.initialize_project(project)
    self.initialize_target_toolchain(self.target)

    self.parse_default_variables(variables)
    self.read_build_prefs()

    #Overrides
    self.objext = '.o'

    #Builders
    self.builders['c'] = self.builder_cc
    self.builders['lib'] = self.builder_lib
    self.builders['multilib'] = self.builder_multicopy
    self.builders['sharedlib'] = self.builder_sharedlib
    self.builders['multisharedlib'] = self.builder_multicopy
    self.builders['bin'] = self.builder_bin
    self.builders['multibin'] = self.builder_multicopy

    #Setup target platform
    self.build_target_toolchain(self.target)

  def name(self):
    return 'clang'

  def parse_prefs(self, prefs):
    super(ClangToolchain, self).parse_prefs(prefs)
    if 'clang' in prefs:
      clangprefs = prefs['clang']
      if 'toolchain' in clangprefs:
        self.toolchain = clangprefs['toolchain']
    if self.target.is_android():
      self.parse_android_prefs(prefs)

  def parse_android_prefs(self, prefs):
    if 'android' in prefs:
      androidprefs = prefs['android']
      if 'ndkpath' in androidprefs:
        self.ndkpath = androidprefs['ndkpath']
      if 'sdkpath' in androidprefs:
        self.sdkpath = androidprefs['sdkpath']
      if 'platformversion' in androidprefs:
        self.platformversion = androidprefs['platformversion']

  def write_variables(self, writer):
    super(ClangToolchain, self).write_variables(writer)
    if self.target.is_android():
      self.write_android_variables(writer)
    writer.variable('toolchain', self.toolchain)
    writer.variable('cc', self.ccompiler)
    writer.variable('ar', self.archiver)
    writer.variable('link', self.linker)
    writer.variable('includepaths', self.make_includepaths(self.includepaths))
    writer.variable('moreincludepaths', '')
    writer.variable('cflags', self.cflags)
    writer.variable('carchflags', '')
    writer.variable('cconfigflags', '')
    writer.variable('arflags', self.arflags)
    writer.variable('ararchflags', '')
    writer.variable('arconfigflags', '')
    writer.variable('linkflags', self.linkflags)
    writer.variable('linkarchflags', '')
    writer.variable('linkconfigflags', '')
    writer.variable('libs', '')
    writer.variable('libpaths', self.make_libpaths(self.libpaths))
    writer.variable('configlibpaths', '')
    writer.variable('archlibs', '')
    writer.variable('oslibs', self.make_libs(self.oslibs))
    writer.newline()

  def write_android_variables(self, writer):
    writer.variable('ndk', self.ndkpath)
    writer.variable('sdk', self.sdkpath)
    writer.variable('sysroot', self.sysroot)

  def write_rules(self, writer):
    super(ClangToolchain, self).write_rules(writer)
    writer.rule('cc', command = self.cccmd, depfile = self.ccdepfile, deps = self.ccdeps, description = 'CC $in')
    writer.rule('ar', command = self.arcmd, description = 'LIB $out')
    writer.rule('link', command = self.linkcmd, description = 'LINK $out')
    writer.rule('so', command = self.linkcmd, description = 'SO $out')
    writer.newline()

  def initialize_target_toolchain(self, target):
    if target.is_android():
      self.initialize_android_toolchain()

  def initialize_android_toolchain(self):
    self.android_sdkpath = os.getenv('NDK_HOME', '')
    self.sdkpath = os.getenv('ANDROID_HOME', '')
    self.platformversion = '21'

  def build_target_toolchain(self, target):
    if target.is_windows():
      self.build_windows_toolchain()
    elif target.is_android():
      self.build_android_toolchain()
    if self.toolchain != '' and not self.toolchain.endswith('/') and not self.toolchain.endswith('\\'):
      self.toolchain += os.sep

  def build_windows_toolchain(self):
    self.cflags += ['-U__STRICT_ANSI__', '-Wno-reserved-id-macro']
    self.oslibs = ['kernel32', 'user32', 'shell32', 'advapi32']

  def build_android_toolchain(self):
    self.sysroot = ''
    self.archiver = 'ar'

    self.cccmd += ' --sysroot=$sysroot'
    self.linkcmd += ' -shared -Wl,-soname,$liblinkname --sysroot=$sysroot'
    self.cflags += ['-fpic', '-ffunction-sections', '-funwind-tables', '-fstack-protector', '-fomit-frame-pointer',
                    '-no-canonical-prefixes', '-Wa,--noexecstack']

    self.linkflags += ['-no-canonical-prefixes', '-Wl,--no-undefined', '-Wl,-z,noexecstack', '-Wl,-z,relro', '-Wl,-z,now']

    self.includepaths += [os.path.join('$ndk', 'sources', 'android', 'native_app_glue'),
                          os.path.join('$ndk', 'sources', 'android', 'cpufeatures')]

    self.oslibs += ['log']

    self.archname = dict()
    self.archname['x86'] = 'x86'
    self.archname['x86-64'] = 'x86_64'
    self.archname['arm6'] = 'arm'
    self.archname['arm7'] = 'arm'
    self.archname['arm64'] = 'arm64'
    self.archname['mips'] = 'mips'
    self.archname['mips64'] = 'mips64'

    self.gcc_toolchainversion = '4.9'

    self.gcc_toolchainname = dict()
    self.gcc_toolchainname['x86'] = 'x86-' + self.gcc_toolchainversion
    self.gcc_toolchainname['x86-64'] = 'x86_64-' + self.gcc_toolchainversion
    self.gcc_toolchainname['arm6'] = 'arm-linux-androideabi-' + self.gcc_toolchainversion
    self.gcc_toolchainname['arm7'] = 'arm-linux-androideabi-' + self.gcc_toolchainversion
    self.gcc_toolchainname['arm64'] = 'aarch64-linux-android-' + self.gcc_toolchainversion
    self.gcc_toolchainname['mips'] = 'mipsel-linux-android-' + self.gcc_toolchainversion
    self.gcc_toolchainname['mips64'] = 'mips64el-linux-android-' + self.gcc_toolchainversion

    self.gcc_toolchainprefix = dict()
    self.gcc_toolchainprefix['x86'] = 'i686-linux-android-'
    self.gcc_toolchainprefix['x86-64'] = 'x86_64-linux-android-'
    self.gcc_toolchainprefix['arm6'] = 'arm-linux-androideabi-'
    self.gcc_toolchainprefix['arm7'] = 'arm-linux-androideabi-'
    self.gcc_toolchainprefix['arm64'] = 'aarch64-linux-android-'
    self.gcc_toolchainprefix['mips'] = 'mipsel-linux-android-'
    self.gcc_toolchainprefix['mips64'] = 'mips64el-linux-android-'

    if self.host.is_windows():
      if os.getenv('PROCESSOR_ARCHITECTURE', 'AMD64').find('64') != -1:
        self.hostarchname = 'windows-x86_64'
      else:
        self.hostarchname = 'windows-x86'
    elif self.host.is_linux():
        localarch = subprocess.check_output(['uname', '-m']).strip()
        if localarch == 'x86_64':
          self.hostarchname = 'linux-x86_64'
        else:
          self.hostarchname = 'linux-x86'
    elif self.host.is_macosx():
      self.hostarchname = 'darwin-x86_64'

    self.toolchain = os.path.join(self.ndkpath, 'toolchains', 'llvm', 'prebuilt', self.hostarchname, 'bin', '')

    buildtools_path = os.path.join(self.sdkpath, 'build-tools')
    buildtools_list = [item for item in os.listdir(buildtools_path) if os.path.isdir(os.path.join(buildtools_path, item))]
    buildtools_list.sort(key = lambda s: map(int, s.split('.')))

    self.buildtools_path = os.path.join(self.sdkpath, 'build-tools', buildtools_list[-1])
    self.android_jar = os.path.join(self.sdkpath, 'platforms', 'android-' + self.platformversion, 'android.jar')

    self.javac = 'javac'
    if self.host.is_windows():
      self.dex = os.path.join(self.buildtools_path, 'dx.bat')
    else:
      self.dex = os.path.join(self.buildtools_path, 'dx' + self.exe_suffix)
    if not os.path.isfile(self.dex):
      self.dex = os.path.join(self.sdkpath, 'tools', 'dx' + self.exe_suffix)
    self.aapt = os.path.join(self.buildtools_path, 'aapt' + self.exe_suffix)
    self.zipalign = os.path.join(self.buildtools_path, 'zipalign' + self.exe_suffix)
    if not os.path.isfile( self.zipalign ):
      self.zipalign = os.path.join(self.sdkpath, 'tools', 'zipalign' + self.exe_suffix)
    self.jarsigner = 'jarsigner'

  def make_android_sysroot_path(self, arch):
    return os.path.join(self.ndkpath, 'platforms', 'android-' + self.platformversion, 'arch-' + self.archname[arch])

  def make_android_gcc_toolchain_path(self, arch):
    return os.path.join(self.ndkpath, 'toolchains', self.gcc_toolchainname[arch], 'prebuilt', self.hostarchname)

  def make_android_gcc_bin_path(self, arch):
    return os.path.join(self.make_android_gcc_toolchain_path(arch), 'bin', self.gcc_toolchainprefix[arch])

  def make_includepaths(self, includepaths):
    if not includepaths is None:
      return ['-I' + self.path_escape(path) for path in list(includepaths)]
    return []

  def make_libpaths(self, libpaths):
    if not libpaths is None:
      if self.target.is_windows():
        return ['-Xlinker /LIBPATH:' + self.path_escape(path) for path in libpaths]
      return ['-L' + self.path_escape(path) for path in libpaths]
    return []

  def make_targetarchflags(self, arch, targettype):
    flags = []
    if self.target.is_android():
      if arch == 'x86':
        flags += ['-target', 'i686-none-linux-android']
      elif arch == 'x86-64':
        flags += ['-target', 'x86_64-none-linux-android']
      elif arch == 'arm6':
        flags += ['-target', 'armv5te-none-linux-androideabi']
      elif arch == 'arm7':
        flags += ['-target', 'armv7-none-linux-androideabi']
      elif arch == 'arm64':
        flags += ['-target', 'aarch64-none-linux-android']
      elif arch == 'mips':
        flags += ['-target', 'mipsel-none-linux-android']
        flags += ['-gcc-toolchain', self.make_android_gcc_toolchain_path(arch)]
      elif arch == 'mips64':
        flags += ['-target', 'mips64el-none-linux-android']
        flags += ['-gcc-toolchain', self.make_android_gcc_toolchain_path(arch)]
    return flags

  def make_carchflags(self, arch, targettype):
    flags = []
    if targettype == 'sharedlib':
      flags += ['-DBUILD_DYNAMIC_LINK=1']
    if self.target.is_android():
      flags += self.make_targetarchflags(arch, targettype)
    return flags

  def make_cconfigflags(self, config, targettype):
    flags = []
    if config == 'debug':
      flags += ['-DBUILD_DEBUG=1', '-g']
    elif config == 'release':
      flags += ['-DBUILD_RELEASE=1', '-O3', '-g', '-funroll-loops']
    elif config == 'profile':
      flags += ['-DBUILD_PROFILE=1', '-O3', '-g', '-funroll-loops']
    elif config == 'deploy':
      flags += ['-DBUILD_DEPLOY=1', '-O3', '-g', '-funroll-loops']
    return flags

  def make_ararchflags(self, arch, targettype):
    flags = []
    return flags

  def make_arconfigflags(self, config, targettype):
    flags = []
    return flags

  def make_linkarchflags(self, arch, targettype):
    flags = []
    if self.target.is_android():
      archlibs = []
      if arch == 'arm7':
        archlibs += ['m_hard']
      else:
        archlibs += ['m']
      archlibs += ['gcc', 'android']
      flags += self.make_libs(archlibs)
    return flags

  def make_linkconfigflags(self, config, targettype):
    flags = []
    if self.target.is_windows():
      if targettype == 'sharedlib':
        flags += ['-Xlinker', '/DLL']
      elif targettype == 'bin':
        flags += ['-Xlinker', '/SUBSYSTEM:CONSOLE']
    if self.target.is_android():
      flags += self.make_targetarchflags(arch, targettype)
    return flags

  def make_libs(self, libs):
    if libs != None:
      return ['-l' + lib for lib in libs]
    return []

  def make_configlibpaths(self, config, arch):
    libpaths = [
      self.libpath,
      os.path.join(self.libpath, config),
      os.path.join(self.libpath, config, arch)
      ]
    return self.make_libpaths(libpaths)

  def cc_variables(self, config, arch, targettype, variables):
    localvariables = []
    if 'includepaths' in variables:
      moreincludepaths = self.make_includepaths(variables['includepaths'])
      if not moreincludepaths == []:
        localvariables += [('moreincludepaths', moreincludepaths)]
    carchflags = self.make_carchflags(arch, targettype)
    if carchflags != []:
      localvariables += [('carchflags', carchflags)]
    cconfigflags = self.make_cconfigflags(config, targettype)
    if cconfigflags != []:
      localvariables += [('cconfigflags', cconfigflags)]
    if self.target.is_android():
      localvariables += [('sysroot', self.make_android_sysroot_path(arch))]
    return localvariables

  def ar_variables(self, config, arch, targettype, variables):
    localvariables = []
    ararchflags = self.make_ararchflags(arch, targettype)
    if ararchflags != []:
      localvariables += [('ararchflags', ararchflags)]
    arconfigflags = self.make_arconfigflags(config, targettype)
    if arconfigflags != []:
      localvariables += [('arconfigflags', arconfigflags)]
    if self.target.is_android():
      localvariables += [('toolchain', self.make_android_gcc_bin_path(arch))]
    return localvariables

  def link_variables(self, config, arch, targettype, variables):
    localvariables = []
    linkarchflags = self.make_linkarchflags(arch, targettype)
    if linkarchflags != []:
      localvariables += [('linkarchflags', linkarchflags)]
    linkconfigflags = self.make_linkconfigflags(config, targettype)
    if linkconfigflags != []:
      localvariables += [('linkconfigflags', linkconfigflags)]
    if 'libs' in variables:
      libvar = self.make_libs(variables['libs'])
      if libvar != []:
        localvariables += [('libs', libvar)]
    localvariables += [('configlibpaths', self.make_configlibpaths(config, arch))]
    return localvariables

  def builder_cc(self, writer, config, arch, targettype, infile, outfile, variables):
    return writer.build(outfile, 'cc', infile, implicit = self.implicit_deps(config, variables), variables = self.cc_variables(config, arch, targettype, variables))

  def builder_lib(self, writer, config, arch, targettype, infiles, outfile, variables):
    return writer.build(outfile, 'ar', infiles, implicit = self.implicit_deps(config, variables), variables = self.ar_variables(config, arch, targettype, variables))

  def builder_sharedlib(self, writer, config, arch, targettype, infiles, outfile, variables):
    return writer.build(outfile, 'so', infiles, implicit = self.implicit_deps(config, variables), variables = self.link_variables(config, arch, targettype, variables))

  def builder_bin(self, writer, config, arch, targettype, infiles, outfile, variables):
    return writer.build(outfile, 'link', infiles, implicit = self.implicit_deps(config, variables), variables = self.link_variables(config, arch, targettype, variables))

def create(host, target, toolchain):
  return ClangToolchain(host, target, toolchain)
