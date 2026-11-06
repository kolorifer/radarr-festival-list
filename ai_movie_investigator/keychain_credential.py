"""One fixed project-bound macOS Keychain lookup inside the supervised runner.

No CLI selector, subprocess, enumeration, UI, unlock or persistence. This returns
an in-process credential only; it supplies no disclosure or spending authority.
"""
from contextlib import contextmanager
from contextvars import ContextVar
import ctypes
import os
import threading
import time
import re
import sys
from .contracts import Refusal,require
from .responses_http import ExplicitCredential

SERVICE='codex.movie-project.openai'
MAX_SECRET=4096
LOOKUP_SECONDS=5
LOOKUP_TIMEOUT_EXIT=124
LOOKUP_TIMEOUT_EXITS={'lookup':80,'framework':81,'interaction_get':82,'interaction_disable':83,
    'query_build':84,'query':85,'data':86,'release':87,'interaction_restore':88}
_STAGE=ContextVar('keychain_lookup_stage',default=None)
_ONE_SHOT=ContextVar('keychain_one_shot_process',default=None)
_CLI_TOKEN=object()
_STAGE_ERRORS={
    'lookup':'keychain_unavailable','framework':'keychain_framework_unavailable',
    'interaction_get':'keychain_interaction_get_failed','interaction_disable':'keychain_interaction_disable_failed',
    'query_build':'keychain_query_build_failed','query':'keychain_query_failed',
    'data':'keychain_data_invalid','release':'keychain_release_failed',
    'interaction_restore':'keychain_interaction_restore_failed',
}


def _note(stage):
    require(stage in _STAGE_ERRORS,'keychain_unavailable')
    current=_STAGE.get()
    if current is not None:current[0]=stage
    # No diagnostic I/O here: a blocked/broken stderr must not prevent cleanup.


@contextmanager
def one_shot_process():
    """Only the actual -m entry opens this process-termination boundary."""
    main=sys.modules.get('__main__');spec=getattr(main,'__spec__',None)
    require(getattr(spec,'name',None)=='ai_movie_investigator.supervised_credit' and
            threading.current_thread() is threading.main_thread() and _ONE_SHOT.get() is None,'keychain_process_required')
    token=_ONE_SHOT.set(_CLI_TOKEN)
    try:yield
    finally:_ONE_SHOT.reset(token)


@contextmanager
def _deadline():
    # Python signal exceptions can wait indefinitely for a blocked ctypes call.
    # This process-local hard stop never prints a secret or waits on stderr.
    require(_ONE_SHOT.get() is _CLI_TOKEN,'keychain_process_required')
    require(threading.current_thread() is threading.main_thread() and _STAGE.get() is None,'keychain_lookup_busy')
    done=threading.Event();gate=threading.Lock();state=[True];stage=['lookup']
    token=_STAGE.set(stage);deadline=time.monotonic()+LOOKUP_SECONDS
    def watchdog():
        if done.wait(max(0,deadline-time.monotonic())):return
        with gate:
            if state[0]:os._exit(LOOKUP_TIMEOUT_EXITS.get(stage[0],LOOKUP_TIMEOUT_EXIT))
    worker=threading.Thread(target=watchdog,name='bounded-keychain-lookup',daemon=True)
    try:
        worker.start()
        _note('lookup')
        yield stage
    finally:
        with gate:
            expired=time.monotonic()>=deadline
            state[0]=False;done.set()
        if worker.ident is not None:worker.join()
        _STAGE.reset(token)
        require(not expired,'keychain_lookup_timeout')



def _frameworks():
    return (ctypes.CDLL('/System/Library/Frameworks/Security.framework/Security'),
            ctypes.CDLL('/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation'))


def _constant(library,name):
    value=ctypes.c_void_p.in_dll(library,name).value
    require(bool(value),'keychain_unavailable')
    return value


def _native(project):
    require(sys.platform=='darwin','keychain_platform')
    _note('framework')
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
    sec.SecKeychainGetUserInteractionAllowed.argtypes=[ctypes.POINTER(ctypes.c_ubyte)]
    sec.SecKeychainGetUserInteractionAllowed.restype=ctypes.c_int32
    sec.SecKeychainSetUserInteractionAllowed.argtypes=[ctypes.c_ubyte]
    sec.SecKeychainSetUserInteractionAllowed.restype=ctypes.c_int32
    original=ctypes.c_ubyte()
    _note('interaction_get')
    require(sec.SecKeychainGetUserInteractionAllowed(ctypes.byref(original))==0,'keychain_interaction_get_failed')
    require(original.value in (0,1),'keychain_interaction_get_failed')
    owned=[];result=ptr();primary=None
    try:
        _note('interaction_disable')
        require(sec.SecKeychainSetUserInteractionAllowed(False)==0,'keychain_interaction_disable_failed')
        _note('query_build')
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
        _note('query')
        status=sec.SecItemCopyMatching(query,ctypes.byref(result))
        if status==-25300:raise Refusal('keychain_missing')
        if status==-25308:raise Refusal('keychain_interaction_required')
        if status in (-25293,-128):raise Refusal('keychain_denied')
        if status==-25291:raise Refusal('keychain_not_available')
        if status==-50:raise Refusal('keychain_parameter_invalid')
        if status==-34018:raise Refusal('keychain_entitlement_missing')
        require(status==0,'keychain_query_failed')
        _note('data')
        require(bool(result.value) and cf.CFGetTypeID(result)==cf.CFDataGetTypeID(),'keychain_data_invalid')
        length=cf.CFDataGetLength(result)
        require(0<length<=MAX_SECRET,'keychain_data_invalid')
        address=cf.CFDataGetBytePtr(result);require(bool(address),'keychain_data_invalid')
        return ctypes.string_at(address,length)
    except Refusal as error:
        primary=error;raise
    except Exception:
        stage=_STAGE.get()
        primary=Refusal(_STAGE_ERRORS.get(stage[0] if stage else 'lookup','keychain_unavailable'))
        raise primary from None
    except BaseException as error:
        primary=error;raise
    finally:
        cleanup=None
        _note('release')
        for item in ([result] if result.value else [])+list(reversed(owned)):
            try:cf.CFRelease(item)
            except BaseException:cleanup=Refusal('keychain_release_failed')
        _note('interaction_restore')
        try:
            if sec.SecKeychainSetUserInteractionAllowed(original.value)!=0:
                cleanup=Refusal('keychain_interaction_restore_failed')
        except BaseException:cleanup=Refusal('keychain_interaction_restore_failed')
        if cleanup is not None:
            if primary is not None:primary.keychain_cleanup_reason=cleanup.args[0]
            else:raise cleanup


def credential(project):
    require(type(project) is str and re.fullmatch(r'proj_[A-Za-z0-9_-]{1,200}',project),'keychain_project')
    with _deadline() as stage:
        try:
            raw=_native(project)
            require(type(raw) is bytes and 0<len(raw)<=MAX_SECRET,'keychain_data_invalid')
            value=raw.decode('ascii')
            require(value.startswith('sk-') and all(33<=ord(c)<=126 for c in value),'keychain_data_invalid')
            return ExplicitCredential(value)
        except Refusal:
            raise
        except Exception:
            # Native exception details never escape; only the fixed stage does.
            raise Refusal(_STAGE_ERRORS.get(stage[0],'keychain_unavailable')) from None
