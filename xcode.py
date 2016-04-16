#!/usr/bin/env python

"""Ninja toolchain abstraction for XCode toolchain"""

import os
import subprocess

import toolchain

def make_target(toolchain, host, target):
  return XCode(toolchain, host, target)

class XCode(object):
  def __init__(self, toolchain, host, target):
    self.toolchain = toolchain
    self.host = host
    self.target = target

  def initialize_toolchain(self):
    self.organisation = ''
    self.bundleidentifier = ''
    self.provisioning = ''
    self.deploymenttarget = ''

  def build_toolchain(self):
    if self.target.is_macosx():
      sdk = 'macosx'
      deploytarget = 'MACOSX_DEPLOYMENT_TARGET=' + self.deploymenttarget
    elif self.target.is_ios():
      sdk = 'iphoneos'
      deploytarget = 'IPHONEOS_DEPLOYMENT_TARGET=' + self.deploymenttarget

    platformpath = subprocess.check_output( [ 'xcrun', '--sdk', sdk, '--show-sdk-platform-path' ] ).strip()
    localpath = platformpath + "/Developer/usr/bin:/Applications/Xcode.app/Contents/Developer/usr/bin:/usr/bin:/bin:/usr/sbin:/sbin"

    self.plist = "PATH=" + localpath + " " + subprocess.check_output( [ 'xcrun', '--sdk', sdk, '-f', 'plutil' ] ).strip()
    self.xcassets = "PATH=" + localpath + " " + subprocess.check_output( [ 'xcrun', '--sdk', sdk, '-f', 'actool' ] ).strip()
    self.xib = "PATH=" + localpath + " " + subprocess.check_output( [ 'xcrun', '--sdk', sdk, '-f', 'ibtool' ] ).strip()
    self.dsymutil = "PATH=" + localpath + " " + subprocess.check_output( [ 'xcrun', '--sdk', sdk, '-f', 'dsymutil' ] ).strip()

    self.plistcmd = 'build/ninja/plist.py --exename $exename --prodname $prodname --bundle $bundleidentifier --target $target --deploymenttarget $deploymenttarget --output $outpath $in'
    if self.target.is_macosx():
      self.xcassetscmd = 'mkdir -p $outpath && $xcassets --output-format human-readable-text --output-partial-info-plist $outplist' \
                         ' --app-icon AppIcon --launch-image LaunchImage --platform macosx --minimum-deployment-target ' + self.deploymenttarget + \
                         ' --target-device mac --compress-pngs --compile $outpath $in >/dev/null'
      self.xibcmd = '$xib --target-device mac --module $module --minimum-deployment-target ' + self.deploymenttarget + \
                    ' --output-partial-info-plist $outplist --auto-activate-custom-fonts' \
                    ' --output-format human-readable-text --compile $outpath $in'
    elif self.target.is_ios():
      self.xcassetscmd = 'mkdir -p $outpath && $xcassets --output-format human-readable-text --output-partial-info-plist $outplist' \
                         ' --app-icon AppIcon --launch-image LaunchImage --platform iphoneos --minimum-deployment-target ' + self.deploymenttarget + \
                         ' --target-device iphone --target-device ipad --compress-pngs --compile $outpath $in >/dev/null'
      self.xibcmd = '$xib --target-device iphone --target-device ipad --module $module --minimum-deployment-target ' + self.deploymenttarget + \
                    ' --output-partial-info-plist $outplist --auto-activate-custom-fonts' \
                    ' --output-format human-readable-text --compile $outpath $in &> /dev/null '
    self.dsymutilcmd = '$dsymutil $in -o $outpath'
    self.codesigncmd = 'build/ninja/codesign.py --target $target --prefs codesign.json --builddir $builddir --binname $binname --config $config $outpath'

  def parse_prefs(self, prefs):
    if self.target.is_ios() and 'ios' in prefs:
      iosprefs = prefs['ios']
      if 'deploymenttarget' in iosprefs:
        self.deploymenttarget = iosprefs['deploymenttarget']
      if 'organisation' in iosprefs:
        self.organisation = iosprefs['organisation']
      if 'bundleidentifier' in iosprefs:
        self.bundleidentifier = iosprefs['bundleidentifier']
      if 'provisioning' in iosprefs:
        self.provisioning = iosprefs['provisioning']
    elif self.target.is_macosx() and 'macosx' in prefs:
      macosxprefs = prefs['macosx']
      if 'deploymenttarget' in macosxprefs:
        self.deploymenttarget = macosxprefs['deploymenttarget']
      if 'organisation' in macosxprefs:
        self.organisation = macosxprefs['organisation']
      if 'bundleidentifier' in macosxprefs:
        self.bundleidentifier = macosxprefs['bundleidentifier']
      if 'provisioning' in macosxprefs:
        self.provisioning = macosxprefs['provisioning']

  def write_variables(self, writer):
    pass

  def write_rules(self, writer):
    pass

  def app(self, toolchain, writer, module, archbins, javasources, outpath, binname, basepath, config, implicit_deps, resources, codesign):
    pass
