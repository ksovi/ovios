package PVE::Storage::LunCmd::OviOSiSCSI;

# iscsi storage running on OviOS Linux
# ovios.org 
# On one of the proxmox nodes:
# 1) Login as root
# 2) ssh-copy-id <ip_of_iscsi_storage>

use strict;
use warnings;

use PVE::Tools qw(run_command file_read_firstline trim dir_glob_regex dir_glob_foreach);

sub get_base;

my $MAX_LUNS = 16864;
my $SETTINGS = undef;
my @ssh_opts = ('-q','-o', 'BatchMode=yes');
my @ssh_cmd = ('/usr/bin/ssh', @ssh_opts);
my @scp_cmd = ('/usr/bin/scp', @ssh_opts);
my $id_rsa_path = '/etc/pve/priv/zfs';
my $tgtadm = '/usr/sbin/tgtadm';
my $logstring= undef;

my $execute_command = sub {
    my ($scfg, $exec, $timeout, $method, @params) = @_;

    my $msg = '';
    my $err = undef;
    my $target;
    my $cmd;
    my $res = ();

    $timeout = 10 if !$timeout;

    my $output = sub {
    my $line = shift;
    $msg .= "$line\n";
    };

    my $errfunc = sub {
    my $line = shift;
    $err .= "$line";
    };
    if ($exec eq 'legacy') {
        $target = 'root@' . $scfg->{portal};
        $cmd = "/usr/bin/ssh -o BatchMode=yes -i $id_rsa_path/$scfg->{portal}_id_rsa $target $method";
        $res = system($cmd);
        return $res;
    } elsif ($exec eq 'scp') {
        $target = 'root@[' . $scfg->{portal} . ']';
        $cmd = [@scp_cmd, '-i', "$id_rsa_path/$scfg->{portal}_id_rsa", '--', $method, "$target:$params[0]"];
    } else {
        $target = 'root@' . $scfg->{portal};
        $cmd = [@ssh_cmd, '-i', "$id_rsa_path/$scfg->{portal}_id_rsa", $target, '--', $method, @params];
    }

    eval {
        run_command($cmd, outfunc => $output, errfunc => $errfunc, timeout => $timeout);
    };
    if ($@) {
        $res = {
            result => 0,
            msg => $err,
        }
    } else {
        $res = {
            result => 1,
            msg => $msg,
        }
    }

    return $res;
};

my $read_config = sub {
    my ($scfg, $timeout) = @_;
    # always getting config from the live state of the system, meaning mapped luns only
    my $msg = '';
    my $err = undef;
    my $luncmd = '/usr/sbin/tgtadm --lld iscsi --mode target --op show | /bin/grep -E "Target | LUN: | Backing store path:"';
    my $target;
    $timeout = 10 if !$timeout;

    my $output = sub {
        my $line = shift;
        $msg .= "$line\n";
    };

    my $errfunc = sub {
        my $line = shift;
        $err .= "$line";
    };

    $target = 'root@' . $scfg->{portal};

    my $cmd = [@ssh_cmd, '-i', "$id_rsa_path/$scfg->{portal}_id_rsa", $target, "$luncmd" ];
    eval {
        run_command($cmd, outfunc => $output, errfunc => $errfunc, timeout => $timeout);
    };
    return $msg;
};

my $get_config = sub {
    my ($scfg) = @_;
    my @conf = undef;
    my $config = $read_config->($scfg, undef);
    return $config;
};

my $parser = sub {
    my ($scfg) = @_;
    my $line = 0;
    my $base = get_base;
    my $config = $get_config->($scfg);
    my @ovioscfg = split "\n", $config;
    my $tn =undef;
    my $cfg_target = 0;
	$logstring = "Starting parsing settings for:  iSCSI PROVIDER: $scfg->{iscsiprovider}, POOL: $scfg->{pool}, PORTAL: $scfg->{portal}, iSCSI TARGET: $scfg->{target}";
	logovios($scfg, $logstring);
    foreach (@ovioscfg) {
        $line++;
        $_ =~ s/^\s+//;
        if ($_ =~ /Target /) {
            my @oviostg = split / /, $_, 3;
            $tn = $oviostg[2];
			$logstring = "Found target : $tn";
			logovios($scfg, $logstring);
            if ($tn eq $scfg->{target} && ! $cfg_target) {
				$logstring = "This target matches. Will be added to SETTINGS, $tn";
				logovios($scfg, $logstring);
                $SETTINGS->{target} = $tn;
                $cfg_target = 1;
            } elsif ($tn eq $scfg->{target} && $cfg_target) {
                die "$line: Parse error [$_]";
            } else {
			    $logstring = "This target doesn't match. Will NOT be added to SETTINGS, $tn";
				logovios($scfg, $logstring);
                $cfg_target = 0;
			}
        } else {
		    if ($cfg_target) {
                my @oviostg = split / /, $_, 7;
                my $lid = $oviostg[1];
                my $indexer = $line;
                if ($lid =~ /\d+/ && $lid != 0 ) {
                    my $path = $ovioscfg[$indexer++];
                    $path =~ s/^\s+|\s+$//g;
                    $path =~ s/Backing store path: //g;
                    #print $lid," ", $path, "\n";
					$logstring = "Found LUN mapped on OviOS : $path with LUN ID: $lid";
					logovios($scfg, $logstring);
                    $indexer = undef;
                    my $conf = undef;
                    $conf->{Path} = $path;
                    if ($conf->{Path} && $conf->{Path} =~ /^$base\/$scfg->{pool}\/([\w\-]+)$/) {
                        $conf->{include} = 1;
						$logstring = "This LUN matches POOL: $scfg->{pool}. Will be added to SETTINGS, $path, with LUN ID $lid";
						logovios($scfg, $logstring);
                    } else {
                        $conf->{include} = 0;
						$logstring = "This LUN doesn't match POOL: $scfg->{pool}. Will NOT be added to SETTINGS, $path";
						logovios($scfg, $logstring);
                    }
					$conf->{lun} = $lid;
                    push @{$SETTINGS->{luns}}, $conf;
                }
		    }		
        }
    }
};

my $get_target_tid = sub {
    my ($scfg) = @_;
    my $tid = undef;
    my $tn =undef;
    my $ovioscommand = '/usr/sbin/tgtadm --lld iscsi --mode target --op show | /bin/grep Target';
    my $res = $execute_command->($scfg, 'ssh', undef, $ovioscommand);
	$logstring = "Parsing targets for target ID configured for POOL: $scfg->{pool}, iSCSI TARGET: $scfg->{target}";
	logovios($scfg, $logstring);
    die $res->{msg} unless $res->{result};
    my @cfg = split "\n", $res->{msg};
    foreach (@cfg) {
        if ($_ =~ /Target /) {
            my @oviostg = split / /, $_, 3;
            $tid =  $oviostg[1];
            $tid =~ s/://g;
            $tn = $oviostg[2];
            if ($tn && $tn eq $scfg->{target}) {
                $tid =~ s/://g;
				$logstring = "Found target $tn to match, and target ID $tid";
				logovios($scfg, $logstring);
                last;
            }
        }
    }
    return $tid;
};

my $get_lu_name = sub {
	my ($scfg, $path) = @_;
    my $used = ();
    my $i;
    for ($i = 1; $i < $MAX_LUNS; $i++) {
        $used->{$i} = 0;
    }
	foreach my $lun (@{$SETTINGS->{luns}}) {
	    $logstring = "Marking LUN ID $lun->{lun} as USED";
		logovios($scfg, $logstring);
        $used->{$lun->{lun}} = 1;
    }
    $SETTINGS->{used} = $used;
    $used = $SETTINGS->{used};
    for ($i = 1; $i < $MAX_LUNS; $i++) {
        last unless $used->{$i};
    }
    $SETTINGS->{used}->{$i} = 1;
    $logstring = "Found Free LUN ID $i for $scfg->{target}";
	logovios($scfg, $logstring);
    return $i;
};

my $init_lu_name = sub {
    my $used = ();

    if (! exists($SETTINGS->{used})) {
        for (my $i = 1; $i < $MAX_LUNS; $i++) {
            $used->{$i} = 0;
        }
        $SETTINGS->{used} = $used;
    }
    foreach my $lun (@{$SETTINGS->{luns}}) {
        $SETTINGS->{used}->{$lun->{lun}} = 1;
    }
};

my $free_lu_name = sub {
    my ($lu_name) = @_;
    my $new;

    foreach my $lun (@{$SETTINGS->{luns}}) {
        if ($lun->{lun} != $lu_name) {
            push @$new, $lun;
        }
    }

    $SETTINGS->{luns} = $new;
    $SETTINGS->{used}->{$lu_name} = 0;
};

my $make_lun = sub {
    my ($scfg, $path) = @_;

    die 'Maximum number of LUNs per target is 16384' if scalar @{$SETTINGS->{luns}} >= $MAX_LUNS;

    my $lun = $get_lu_name->($scfg, $path);
    my $conf = {
        lun => $lun,
        Path => $path,
        include => 1,
    };
    push @{$SETTINGS->{luns}}, $conf;

    return $conf;
};

my $list_view = sub {
    my ($scfg, $timeout, $method, @params) = @_;
    my $lun = undef;

    my $object = $params[0];
    foreach my $lun (@{$SETTINGS->{luns}}) {
        next unless $lun->{include} == 1;
        if ($lun->{Path} =~ /^$object$/) {
            return $lun->{lun} if (defined($lun->{lun}));
            die "$lun->{Path}: Missing LUN";
        }
    }

    return $lun;
};

my $list_lun = sub {
    my ($scfg, $timeout, $method, @params) = @_;
    my $name = undef;
    my $object = $params[0];
	if ( $SETTINGS->{target} ne $scfg->{target} ) {
        $logstring = "Changing config from $SETTINGS->{target} to $scfg->{target}";
        logovios($scfg, $logstring);
		$SETTINGS = undef;
        $parser->($scfg);
    }
    foreach my $lun (@{$SETTINGS->{luns}}) {
		$logstring = "Checking for: POOL: $scfg->{pool}, iSCSI TARGET: $scfg->{target}, Found LUN in SETTINGS: $lun->{Path} , Include: $lun->{include}";
		logovios($scfg, $logstring);
        next unless $lun->{include} == 1;
        if ($lun->{Path} =~ /^$object$/) {
			$logstring = "Returning LUN: $lun->{Path}";
			logovios($scfg, $logstring);
            return $lun->{Path};
        }
    }
	$logstring = "Didn't find any LUNs to list, retuning none";
	logovios($scfg, $logstring);
    return $name;
};

my $create_lun = sub {
    my ($scfg, $timeout, $method, @params) = @_;

    if ($list_lun->($scfg, $timeout, $method, @params)) {
        die "$params[0]: LUN exists";
    }
    my $lun = $params[0];
    $lun = $make_lun->($scfg, $lun);
    my $tid = $get_target_tid->($scfg);
    my $path = "$lun->{Path}";
    
    @params = ('--lld', 'iscsi', '--op', 'new','--mode', 'logicalunit',  "--tid $tid", "--lun $lun->{lun}", '-b', $path);
    my $res = $execute_command->($scfg, 'ssh', $timeout, $tgtadm, @params);
    do {
        $free_lu_name->($lun->{lun});
        die $res->{msg};
    } unless $res->{result};
    # update config 
    my $tgtovadm = "'/usr/sbin/tgt-ovadmin --dump > /etc/tgt/targets.conf'";
    @params = ("");
    $execute_command->($scfg, 'legacy', undef, $tgtovadm);
	$logstring = "Mapped LUN $path to Target $scfg->{target} with Lun ID: $lun->{lun}";
	logovios($scfg, $logstring);
	# ovios flags
    my $target_name = $scfg->{target};
    my @dataset = split'/', $path;
    my $ds = "$dataset[-2]/$dataset[-1]";
    my $zfs = "/usr/sbin/zfs";
    @params = (" set lun:mapped=yes lun:type=proxmox lun:id=$lun->{lun} lun:tg-name=$target_name $ds");
    $execute_command->($scfg, 'ssh', $timeout, $zfs, @params);
    return $res->{msg};
};

my $delete_lun = sub {
    my ($scfg, $timeout, $method, @params) = @_;
    my $res = {msg => undef};

    my $path = $params[0];
    my $tid = $get_target_tid->($scfg);

    foreach my $lun (@{$SETTINGS->{luns}}) {
        if ($lun->{Path} eq $path) {
            @params = ('--lld', 'iscsi', '--op', 'delete', '--mode', 'logicalunit', "--tid $tid", "--lun $lun->{lun}");
            $res = $execute_command->($scfg, 'ssh', $timeout, $tgtadm, @params);
            if ($res->{result}) {
				$logstring = "UnMapped LUN $path from Target $scfg->{target} and Lun ID: $lun->{lun}";
				logovios($scfg, $logstring);
                $free_lu_name->($lun->{lun});
                last;
            } else {
                die $res->{msg};
            }
        }
    }
    # update config 
    my $tgtovadm = "'/usr/sbin/tgt-ovadmin --dump > /etc/tgt/targets.conf'";
    @params = ("");
    $execute_command->($scfg, 'legacy', undef, $tgtovadm);
    return $res->{msg};
};

my $import_lun = sub {
    my ($scfg, $timeout, $method, @params) = @_;
    return $create_lun->($scfg, $timeout, $method, @params);
};

my $modify_lun = sub {
    my ($scfg, $timeout, $method, @params) = @_;
    my $lun;
    my $res;

    my $path = $params[1];
    my $tid = $get_target_tid->($scfg);

    foreach my $cfg (@{$SETTINGS->{luns}}) {
        if ($cfg->{Path} eq $path) {
            $lun = $cfg;
            last;
        }
    }
    @params = ('--lld', 'iscsi', '--op', 'delete', '--mode', 'logicalunit', "--tid $tid", "--lun $lun->{lun}");
    $res = $execute_command->($scfg, 'ssh', $timeout, $tgtadm, @params);
    die $res->{msg} unless $res->{result};
    # ovios flags
    my $target_name = $scfg->{target};
    my @dataset = split'/', $path;
    my $ds = "$dataset[-2]/$dataset[-1]";
	# ovios unmap lun
    my $zfs = "/usr/sbin/zfs";
    @params = (" set lun:mapped=no lun:type=none lun:id=none lun:tg-name=none $ds");
    $execute_command->($scfg, 'ssh', $timeout, $zfs, @params);
    $path = "$lun->{Path}";
    @params = ('--lld', 'iscsi', '--op', 'new','--mode', 'logicalunit',  "--tid $tid", "--lun $lun->{lun}", '-b', $path);
    $res = $execute_command->($scfg, 'ssh', $timeout, $tgtadm, @params);
    die $res->{msg} unless $res->{result};
	# ovios map lun
    @params = (" set lun:mapped=yes lun:type=proxmox lun:id=$lun->{lun} lun:tg-name=$target_name $ds");
    $execute_command->($scfg, 'ssh', $timeout, $zfs, @params);
	# update config 
    my $tgtovadm = "'/usr/sbin/tgt-ovadmin --dump > /etc/tgt/targets.conf'";
    @params = ("");
    $execute_command->($scfg, 'legacy', undef, $tgtovadm);
    return $res->{msg};
};

my $add_view = sub {
    my ($scfg, $timeout, $method, @params) = @_;

    return '';
};

my $get_lun_cmd_map = sub {
    my ($method) = @_;

    my $cmdmap = {
        create_lu   =>  { cmd => $create_lun },
        delete_lu   =>  { cmd => $delete_lun },
        import_lu   =>  { cmd => $import_lun },
        modify_lu   =>  { cmd => $modify_lun },
        add_view    =>  { cmd => $add_view },
        list_view   =>  { cmd => $list_view },
        list_lu     =>  { cmd => $list_lun },
    };

    die "unknown command '$method'" unless exists $cmdmap->{$method};

    return $cmdmap->{$method};
};

sub run_lun_command {
    my ($scfg, $timeout, $method, @params) = @_;
    $parser->($scfg) unless $SETTINGS;
    my $cmdmap = $get_lun_cmd_map->($method);
    my $msg = $cmdmap->{cmd}->($scfg, $timeout, $method, @params);
    return $msg;
}

sub get_base {
    return '/dev/zvol';
}

sub logovios {
    my ($scfg,$logstring) = @_;
    if ($scfg->{remotelogging}) {
        my $datestr = localtime();
        my $logcmd="'/bin/echo  $datestr $logstring >> /var/log/proxmox-agent.log'";
        $execute_command->($scfg, 'legacy', undef, $logcmd);
    } else {
    }
}

1;


