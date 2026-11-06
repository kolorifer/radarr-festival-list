"""One fixed project-bound macOS Keychain lookup inside the supervised runner.

No CLI selector, subprocess, enumeration, UI, unlock or persistence. This returns
an in-process credential only; it supplies no disclosure or spending authority.
"""
import ctypes
import re
import sys
from .contracts import Refusal,require
from .responses_http import ExplicitCredential

SERVICE='codex.movie-project.openai'
MAX_SECRET=4096


def _frameworks():
    return (ctypes.CDLL('/System/Library/Frameworks/Security.framework/Security'),
            ctypes.CDLL('/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation'))


def _constant(library,name):
    value=ctypes.c_void_p.in_dll(library,name).value
    require(bool(value),'keychain_unavailable')
    return value


def _native(project):
    require(sys.platform=='darwin','keychain_platform')
    sec,cf=_frameworks();ptr=ctypes.c_void_p;index=ctypes.c_long
    functions={
        'CFStringCreateWithCString':([ptr,ctypes.c_char_p,ctypes.c_uint32],ptr),
        'CFDictionaryCreateMutable':([ptr,index,ptr,ptr],ptr),
        'CFDictionarySetValue':([ptr,ptr,ptr],None),
        'CFGetTypeID':([ptr],ctypes.c_ulong),
        'CFDataGetTypeID':([],ctypes.c_ulong),
        'CFDataGetLength':([ptr],index),
        'CFDataGetBytePtr':([ptr],ptr),
        'CFRelease':([ptr],None),
    }
    for name,(args,result) in functions.items():
        fn=getattr(cf,name);fn.argtypes=args;fn.restype=result
    sec.SecItemCopyMatching.argtypes=[ptr,ctypes.POINTER(ptr)]
    sec.SecItemCopyMatching.restype=ctypes.c_int32
    owned=[];result=ptr()
    try:
        def string(value):
            item=cf.CFStringCreateWithCString(None,value.encode('utf-8'),0x08000100)
            require(bool(item),'keychain_unavailable');owned.append(item);return item
        service,account=string(SERVICE),string(project)
        # NULL callbacks: owned strings stay alive until the dictionary is released.
        query=cf.CFDictionaryCreateMutable(None,0,None,None)
        require(bool(query),'keychain_unavailable');owned.append(query)
        entries=(('kSecClass',_constant(sec,'kSecClassGenericPassword')),
                 ('kSecAttrService',service),('kSecAttrAccount',account),
                 ('kSecReturnData',_constant(cf,'kCFBooleanTrue')),
                 ('kSecMatchLimit',_constant(sec,'kSecMatchLimitOne')),
                 ('kSecUseAuthenticationUI',_constant(sec,'kSecUseAuthenticationUIFail')))
        for key,value in entries:cf.CFDictionarySetValue(query,_constant(sec,key),value)
        status=sec.SecItemCopyMatching(query,ctypes.byref(result))
        if status==-25300:raise Refusal('keychain_missing')
        if status==-25308:raise Refusal('keychain_interaction_required')
        if status in (-25293,-128):raise Refusal('keychain_denied')
        require(status==0,'keychain_unavailable')
        require(bool(result.value) and cf.CFGetTypeID(result)==cf.CFDataGetTypeID(),'keychain_data_invalid')
        length=cf.CFDataGetLength(result)
        require(0<length<=MAX_SECRET,'keychain_data_invalid')
        address=cf.CFDataGetBytePtr(result);require(bool(address),'keychain_data_invalid')
        return ctypes.string_at(address,length)
    finally:
        if result.value:cf.CFRelease(result)
        for item in reversed(owned):cf.CFRelease(item)


def credential(project):
    require(type(project) is str and re.fullmatch(r'proj_[A-Za-z0-9_-]{1,200}',project),'keychain_project')
    try:
        raw=_native(project)
        require(type(raw) is bytes and 0<len(raw)<=MAX_SECRET,'keychain_data_invalid')
        value=raw.decode('ascii')
        require(value.startswith('sk-') and all(33<=ord(c)<=126 for c in value),'keychain_data_invalid')
        return ExplicitCredential(value)
    except Refusal:
        raise
    except Exception:
        # Never surface native error text, paths or secret bytes.
        raise Refusal('keychain_unavailable') from None
