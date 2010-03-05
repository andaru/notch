#!/usr/bin/env python
#
# Copyright 2009 Andrew Fort. All Rights Reserved.

"""Mr. CLI: A Multi Router Command-Line Interface.

This networking tool is a Notch front-end providing a command-line
interface proxy to multiple routers, switches or other devices known
by Notch Agents.
"""


import cmd
import optparse

import notch.client


class CommandLineInterface(cmd.Cmd):
    """Mr. CLI's command-line interface."""

    _prompt_prefix = 'mr.cli'
    prompt = '%s [targets: 0] > ' % _prompt_prefix
    intro = ('Welcome to Mr. CLI. Type "help" to get help.')
    option_prefix = '/'

    def __init__(self, notch, completekey='tab', stdin=None, stdout=None):
        self.notch = notch
        self._targets = []

        cmd.Cmd.__init__(self,
                         completekey=completekey, stdin=stdin, stdout=stdout)

    def _notch_callback(self, request, *args, **kwargs):
        if request is not None:
            self.stdout.write('%s:\n%s\n'
                              % (request.arguments.get('device_name'),
                                 request.result))

    def do_cmd(self, arg):
        """Executes a command on the target devices."""
        if self.notch is None:
            self.stdout.write('Error: no Notch connection to execute requests.')
        elif not self._targets:
            self.stdout.write('Error: no targets to execute command on.')
        else:
            self.execute_command(arg, self._targets)

    def do_EOF(self, arg):
        """Sending EOF (Ctrl-D) will exit Mr. CLI."""
        raise SystemExit(0)

    def do_exit(self, unused_arg):
        """Exits Mr. CLI."""
        self.do_EOF(None)

    def do_logout(self, unused_arg):
        """Exits Mr. CLI."""
        self.do_EOF(None)

    def help_cmd(self):
        msg = ('Execute a command as if entered on all target devices.\n\n'
               'Usage:\n'
               '  cmd <command>\n\n'
               'Examples:\n'
               '  > cmd show version\n'
               '    - Get the software/hardware status from all targets.\n\n'
               '  > cmd ping 10.1.1.1\n'
               '    - Have all targets ping a single address.\n')
        self.stdout.write(msg)

    def help_EOF(self):
        self.stdout.write(self.do_EOF.__doc__+'\n')

    def help_help(self):
        self.stdout.write('I\'m not sure I can help you with help on help.\n')

    def help_targets(self):
        msg = ('Display or modify the device target list for commands.\n\n'
               'Usage:\n'
               '  targets [space separated list of names]\n\n'
               'Examples:\n'
               '  > targets\n'
               '    - Display the current target list.\n\n'
               '  > targets rtr1.bne rtr2.syd\n'
               '    - Sets the target list to rtr1.bne, rtr2.syd.\n')
        self.stdout.write(msg)

    def execute_command(self, command, targets):
        for target in targets:
            method_args = {'device_name': target,
                           'command': command}
            r = notch.client.client.NotchRequest(
                'command', arguments=method_args, callback=self._notch_callback)
            self.notch.exec_request(r)
        self.notch.wait_all()

    def default(self, line):
        self.stdout.write('Error: Unknown command: %s. Try "help".\n' % line)

    def emptyline(self):
        pass

    def do_targets(self, arg):
        """Show or modify the list of target devices commands go to."""
        if not arg:
            if not self._targets:
                self.stdout.write('There are no targets.\n')
            else:
                self.stdout.write('Targets: %s\n' % self._targets)
        else:
            self._targets = arg.strip().split()
            self.prompt = '%s [targets: %d] > ' % (self._prompt_prefix,
                                                   len(self._targets))
            self.stdout.write('Targets changed to: %s\n' % self._targets)


def get_option_parser():
    parser = optparse.OptionParser()
    parser.usage = (
        '%prog <comma-separated list of agent host:port pairs>')
    return parser


if __name__ == '__main__':
    option_parser = get_option_parser()
    _, args = option_parser.parse_args()
    if not args:
        print option_parser.get_usage()
        raise SystemExit(1)

    agents = ' '.join(args).split(',')
    for i, a in enumerate(agents):
        agents[i] = a.lstrip()

    try:
        nc = notch.client.NotchClient(agents)
    except notch.client.NoAgentsError, e:
        print option_parser.get_usage()
        raise SystemExit(1)

    cli = CommandLineInterface(nc)
    try:
        cli.cmdloop()
    except KeyboardInterrupt:
        print '\n\nTerminated.'
    except SystemExit:
        print '\n\nBye.'
