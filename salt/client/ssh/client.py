# -*- coding: utf-8 -*-

# Import Python libs
from __future__ import absolute_import
import os
import copy
import logging

# Import Salt libs
import salt.config
import salt.syspaths as syspaths
from salt.exceptions import SaltClientError  # Temporary

log = logging.getLogger(__name__)


class SSHClient(object):
    '''
    Create a client object for executing routines via the salt-ssh backend

    .. versionadded:: 2015.5.0
    '''
    def __init__(self,
                 c_path=os.path.join(syspaths.CONFIG_DIR, 'master'),
                 mopts=None,
                 disable_custom_roster=False):
        if mopts:
            self.opts = mopts
        else:
            if os.path.isdir(c_path):
                log.warning(
                    '{0} expects a file path not a directory path({1}) to '
                    'it\'s \'c_path\' keyword argument'.format(
                        self.__class__.__name__, c_path
                    )
                )
            self.opts = salt.config.client_config(c_path)

        # Salt API should never offer a custom roster!
        self.opts['__disable_custom_roster'] = disable_custom_roster

    def sanitize_kwargs(self, kwargs):
        roster_vals = [
            ('host', str),
            ('ssh_user', str),
            ('ssh_passwd', str),
            ('ssh_port', int),
            ('ssh_sudo', bool),
            ('ssh_sudo_user', str),
            ('ssh_priv', str),
            ('ssh_priv_passwd', str),
            ('ssh_identities_only', bool),
            ('ssh_remote_port_forwards', str),
            ('ssh_options', list),
            ('roster_file', str),
            ('rosters', list),
            ('ignore_host_keys', bool),
            ('raw_shell', bool),
        ]
        sane_kwargs = {}
        for name, kind in roster_vals:
            if name not in kwargs:
                continue
            try:
                val = kind(kwargs[name])
            except ValueError:
                log.warn("Unable to cast kwarg %s", name)
                continue
            if kind is bool or kind is int:
                sane_kwargs[name] = val
            elif kind is str:
                if val.find('ProxyCommand') != -1:
                    log.warn("Filter unsafe value for kwarg %s", name)
                    continue
                sane_kwargs[name] = val
            elif kind is list:
                sane_val = []
                for item in val:
                    # This assumes the values are strings
                    if item.find('ProxyCommand') != -1:
                        log.warn("Filter unsafe value for kwarg %s", name)
                        continue
                    sane_val.append(item)
                sane_kwargs[name] = sane_val
        return sane_kwargs

    def _prep_ssh(
            self,
            tgt,
            fun,
            arg=(),
            timeout=None,
            expr_form='glob',
            kwarg=None,
            **kwargs):
        '''
        Prepare the arguments
        '''
        kwargs = self.sanitize_kwargs(kwargs)
        opts = copy.deepcopy(self.opts)
        opts.update(kwargs)
        if timeout:
            opts['timeout'] = timeout
        arg = salt.utils.args.condition_input(arg, kwarg)
        opts['argv'] = [fun] + arg
        opts['selected_target_option'] = expr_form
        opts['tgt'] = tgt
        opts['arg'] = arg
        return salt.client.ssh.SSH(opts)

    def cmd_iter(
            self,
            tgt,
            fun,
            arg=(),
            timeout=None,
            expr_form='glob',
            ret='',
            kwarg=None,
            **kwargs):
        '''
        Execute a single command via the salt-ssh subsystem and return a
        generator

        .. versionadded:: 2015.5.0
        '''
        ssh = self._prep_ssh(
                tgt,
                fun,
                arg,
                timeout,
                expr_form,
                kwarg,
                **kwargs)
        for ret in ssh.run_iter(jid=kwargs.get('jid', None)):
            yield ret

    def cmd(
            self,
            tgt,
            fun,
            arg=(),
            timeout=None,
            expr_form='glob',
            kwarg=None,
            **kwargs):
        '''
        Execute a single command via the salt-ssh subsystem and return all
        routines at once

        .. versionadded:: 2015.5.0
        '''
        ssh = self._prep_ssh(
                tgt,
                fun,
                arg,
                timeout,
                expr_form,
                kwarg,
                **kwargs)
        final = {}
        for ret in ssh.run_iter(jid=kwargs.get('jid', None)):
            final.update(ret)
        return final

    def cmd_sync(self, low):
        '''
        Execute a salt-ssh call synchronously.

        .. versionadded:: 2015.5.0

        WARNING: Eauth is **NOT** respected

        .. code-block:: python

            client.cmd_sync({
                'tgt': 'silver',
                'fun': 'test.ping',
                'arg': (),
                'expr_form'='glob',
                'kwarg'={}
                })
            {'silver': {'fun_args': [], 'jid': '20141202152721523072', 'return': True, 'retcode': 0, 'success': True, 'fun': 'test.ping', 'id': 'silver'}}
        '''

        kwargs = copy.deepcopy(low)

        for ignore in ['tgt', 'fun', 'arg', 'timeout', 'expr_form', 'kwarg']:
            if ignore in kwargs:
                del kwargs[ignore]

        return self.cmd(low['tgt'],
                        low['fun'],
                        low.get('arg', []),
                        low.get('timeout'),
                        low.get('expr_form'),
                        low.get('kwarg'),
                        **kwargs)

    def cmd_async(self, low, timeout=None):
        '''
        Execute aa salt-ssh asynchronously

        WARNING: Eauth is **NOT** respected

        .. code-block:: python

            client.cmd_sync({
                'tgt': 'silver',
                'fun': 'test.ping',
                'arg': (),
                'expr_form'='glob',
                'kwarg'={}
                })
            {'silver': {'fun_args': [], 'jid': '20141202152721523072', 'return': True, 'retcode': 0, 'success': True, 'fun': 'test.ping', 'id': 'silver'}}
        '''
        # TODO Not implemented
        raise SaltClientError
