#!/usr/bin/python

"""Convert mbox input into elisp snippets for an email address database.
See http://svn.red-bean.com/repos/kfogel/trunk/bin/README.mailaprop
for what this is all about.

Usage: mailaprop.py < STDIN > OUTPUT
"""

# TODO: Consider using Flanker (https://github.com/mailgun/flanker)
# to parse the email addreses.  Description:
#
#   "Flanker is an open source parsing library written in Python
#   by the Mailgun Team. Flanker currently consists of an address
#   parsing library (flanker.addresslib) as well as a MIME parsing
#   library (flanker.mime)."
#
# And consider using Nikolaj Schumacher's "Recent Addresses" package:
#   http://nschum.de/src/emacs/recent-addresses/
#   http://nschum.de/src/emacs/recent-addresses/recent-addresses.el
#   (or see https://github.com/nschum/recent-addresses.el)

import os
import sys
import re
import string
import email.Utils
import email.Parser
import getopt

# The various forms of email address WITH NAME IN FRONT are:
#
#    J. Random <jrandom@jrandom.com>
#    J. "NickName" Random <jrandom@jrandom.com>
#    "J. Random" <jrandom@jrandom.com>
#    'J. Random' <jrandom@jrandom.com>
#    "'J. Random'" <jrandom@jrandom.com>
#
# The forms WITH NAME IN REAR are:
#
#    <jrandom@jrandom.com> (J. Random)
#    jrandom@jrandom.com (J. Random)
#
# The forms WITHOUT NAME are:
#
#    <jrandom@jrandom.com>
#    jrandom@jrandom.com
#
# And sometimes we get the email address duplicated as the name:
#
#    "jrandom@jrandom.com" <jrandom@jrandom.com>
#    jrandom@jrandom.com <jrandom@jrandom.com>
#
# Fortunately, we have the email.Utils.getaddresses() function to
# parse them.

def case_preferred_str(str_a, str_b, style=None):
    """Return the case-better variant of STR_A and STR_B based on STYLE.
    STYLE is "name" or "addr".  If no clear case preference, return STR_A.
    Right now, our preference for names is for upper-case, and for
    addresses is lower case.  E.g., If the first letter upper-case (or
    lower case, for addresses) in one string and not the other, that is
    enough to prefer the first string."""
    if ((str_a.isupper() and str_b.isupper())
        or (str_a.islower() and str_b.islower())):
        if style == "name":
            return str_a
        else:
            return str_b
    if str_a[0].isupper() and not str_b[0].isupper():
        if style == "name":
            return str_a
        else:
            return str_b
    if (not str_a[0].isupper()) and str_b[0].isupper():
        if style == "name":
            return str_b
        else:
            return str_a
    if str_a.isupper() and not str_b.isupper():
        if style == "name":
            return str_a
        else:
            return str_b
    elif (not str_a.isupper()) and str_b.isupper():
        if style == "name":
            return str_b
        else:
            return str_a
    else:
        return str_a

def case_preferred_name(name_a, name_b):
    """Return the case-better variant of NAME_A and NAME_B.
    If either of the names is None, return the other (which
  means if both are None, then return None)."""
    if (name_a is not None) and (name_b is None):
        return name_a
    elif name_a is None:
        return name_b
    else:
        return case_preferred_str(name_a, name_b, style="name")

def case_preferred_addr(addr_a, addr_b):
    """Return the case-better variant of ADDR_A and ADDR_B."""
    return case_preferred_str(addr_a, addr_b, style="addr")

# We need this for the same reason we always do.
month_vals = {
    "jan" : 1,
    "feb" : 2,
    "mar" : 3,
    "apr" : 4,
    "may" : 5,
    "jun" : 6,
    "jul" : 7,
    "aug" : 8,
    "sep" : 9,
    "oct" : 10,
    "nov" : 11,
    "dec" : 12
}

# Regexp matching one of our canonical dates
# (always a string like "2011 Nov 07").
canonical_date_re = re.compile("^([0-9][0-9][0-9][0-9]) "
                               + "(Jan"
                               + "|Mar"
                               + "|Apr"
                               + "|May"
                               + "|Jun"
                               + "|Jul"
                               + "|Aug"
                               + "|Sep"
                               + "|Oct"
                               + "|Nov"
                               + "|Dec)"
                               +" ([0-9][0-9])$")

def date_as_number(date_str):
    """Convert DATE_STR (like "2011 Nov 07") to an int (like 20111107).
    Return 0 if DATE_STR is in any way non-canonical."""
    if date_str is None:
        return 0
    m = canonical_date_re.match(date_str)
    if m is not None:
        return (  (int(m.group(1)) * 10000)
                + (month_vals[m.group(2).lower()] * 100)
                + int(m.group(3)))
    else:
        return 0


def later_date (date_a, date_b):
    """Return the later of DATE_A and DATE_B.  Each date is a string,
e.g., "2015 Jul 07", or else None.  If neither is later, return DATE_A."""
    # The try/except is due to having encountered this error:
    #
    # Traceback (most recent call last):
    #   File "/home/kfogel/bin/mailaprop/mailaprop.py", line 245, \
    #     in <module> main()
    #   File "/home/kfogel/bin/mailaprop/mailaprop.py", line 224, \
    #     in main absorb_message(msg, addresses)
    #   File "/home/kfogel/bin/mailaprop/mailaprop.py", line 208, \
    #     in absorb_message existing_ah.maybe_merge(new_ah, addresses)
    #   File "/home/kfogel/bin/mailaprop/mailaprop.py", line 154, \
    #     in maybe_merge self.date = later_date(self.date, other_ah.date)
    #   File "/home/kfogel/bin/mailaprop/mailaprop.py", line 70, \
    #     in later_date if int(date_a[0:4]) > int(date_b[0:4]):
    # ValueError: invalid literal for int() with base 10: '17.6'
    try:
        if date_a is None:
            return date_b
        if date_b is None:
            return date_a
        if int(date_a[0:4]) > int(date_b[0:4]):
            return date_a
        if int(date_a[0:4]) < int(date_b[0:4]):
            return date_b
        if month_vals[date_a[5:8].lower()] > month_vals[date_b[5:8].lower()]:
            return date_a
        if month_vals[date_a[5:8].lower()] < month_vals[date_b[5:8].lower()]:
            return date_b
        if int(date_a[9:11]) > int(date_b[9:11]):
            return date_a
        if int(date_a[9:11]) < int(date_b[9:11]):
            return date_b
    except (ValueError):
        # sys.stderr.write("DEBUG: ValueError case\n")
        # sys.stderr.write("DEBUG: date a: %s\n" % date_a)
        # sys.stderr.write("DEBUG: date b: %s\n" % date_b)
        # sys.stderr.write("DEBUG:\n")
        pass
    except (KeyError):
        # sys.stderr.write("DEBUG: KeyError case\n")
        # sys.stderr.write("DEBUG: date a: %s\n" % date_a)
        # sys.stderr.write("DEBUG: date b: %s\n" % date_b)
        # sys.stderr.write("DEBUG:\n")
        #
        # Believe it or not, in all the email I've sent and received,
        # there is exactly one case where this gets stimulated:
        #
        # DEBUG: KeyError case
        # DEBUG: date a: 2014 Apr 10
        # DEBUG: date b: 2014 08 15
        pass
    # Either they're the same date, or we can't tell.
    return date_a

def name_from_address(full_addr):
    """Return just the name portion of FULL_ADDR."""
    idx = full_addr.find("<")
    if idx == -1:
        return None
    else:
        return full_addr[0:(idx - 1)]

def address_from_address(full_addr):
    """Return just the address portion of FULL_ADDR."""
    idx = full_addr.find("<")
    if idx == -1:
        return full_addr
    else:
        return full_addr[(idx + 1):(len(full_addr) - 1)]


class AddressDifference(Exception):
    """Two email addresses differ by more than case."""
    pass

class FullAddressDuplication(Exception):
    """Programmer error: two instances of same full address found in pool.
    We must see the head of my order; he will know what to do."""
    pass

class AddressHistory:
    """All the name/case variants and their encounter dates, for one address."""
    def __init__(self, name, addr, date, sent_to=False):
        """NAME is the real name portion of an email address; it may be None.
        ADDR is the address portion (without the angle brackets); DATE is
        either None or a canonical date string (e.g., "2015 Jul 07").
        If SENT_TO is not False, count this as an address count I've
        sent to; otherwise, count it as one I've merely seen."""
        if ((name is not None) and
            (('@' in name)
             or (name == "\\")
             or (len(name) > 2 and name[0] == "=" and name[1] == "?"))):
            # We don't store names that are really just duplicates of the
            # email address, because we already have the address and we
            # don't want the fake name to shadow a real name later.  We also
            # don't currently store MIME-encoded representations of ISO or
            # UTF names, because the encoding will make them hard to
            # complete; however, the right long-term solution there is to
            # decode them into a canonical UTF-8 string and store that.
            name = None

        self.key_addr = addr.lower()  # The address is always lower case as a key.

        # Map each "NAME <ADDR>" combination associated with this
        # address to a three-element tuple consisting of: the date (a
        # string) that combination was last seen, its total sent-to
        # count, and its total received-from count.
        #
        # While we could technically just record the NAME, sometimes
        # there are interesting capitalization variants with ADDRESS
        # too, that we would want to preserve, so we record both.
        self.full_addrs = {}
        if name is not None:
            self.full_addrs[self.key_addr] = ["N/A", 0, 0,]
        self.update(name, addr, date, sent_to)

    def make_full_addr(self, addr, name):
        """Return a full address created from ADDR and NAME."""
        if name is not None:
            return name + " <" + addr + ">"
        else:
            return addr

    def __str__(self):
        """Return a string representation of self."""
        return "%s" % self.key_addr

    def update(self, name, addr, date, sent_to=False):
        """Update self if necessary based on ADDR, NAME, and DATE.
        DATE is either None or string like, e.g., "2015 Jul 07".
        Raise an AddressDifference error if self does not match ADDR.
        If SENT_TO is not False, increase this address's count for my
        sending to it; otherwise just increase its regular count."""
        key_addr = addr.lower()  # canonicalize the key, as usual
        # Sanity check -- this should never fail.
        if self.key_addr != key_addr:
            raise AddressDifference("'%s' and '%s' differ by more than case"
                                    % (self.addr, other_ah.addr))
        candidate_full_addr = self.make_full_addr(addr, name)
        incr_sent  = 0
        incr_recv = 0
        if sent_to: 
            incr_sent = 1
        else: 
            incr_recv = 1
        # This conditional guards against ("\ | 2009 May 05" . "\"),
        # which actually occurs due to Chong Yidong's post to emacs-devel@
        # on 5 May 2009 with message-id "<87ab5rvds7.fsf@cyd.mit.edu>".
        # (This is mail/emacs/devel/93029 in my mail tree.)  There's
        # another one that looks like ("\ | 2009 Apr 09" . "\"), that I
        # think comes even earlier now, but I don't know what message.
        #
        # A better solution would be to quote backslashes in the printing
        # loop, but I'm too lazy to count them right now.
        #
        # It also attempts (I think?) to guard against this recurrent
        # problem sexp:
        #
        #   ("chromatic betsy,                                            \
        #   \\"Greg Wilson <gvwilson@cs.toronto.edu> | 2007 May 25" .     \
        #   "betsy, chromatic, \"Greg Wilson <gvwilson@cs.toronto.edu>")
        #
        # That really needs to be debugged once and for all.
        if (candidate_full_addr is not None
            and candidate_full_addr != "\\"
            and candidate_full_addr.find("#") == -1):
            # If we already have this full address, maybe just update it.
            # Updating includes 1) updating to the most recent date,
            # sent count, and received count, and 2) making sure only
            # the most case-canonical version of the full address is kept.
            #
            # Because of (2), by the end of this loop, there will be
            # only one instance of this name+address in self.full_addrs, 
            # and it will be the case-best version.  Therefore, on any
            # given call, candidate_full_addr can only match once; if
            # it matches more than once, something is wrong, and we
            # will raise a FullAddressDuplication exception.
            matched = False
            for other_full_addr in self.full_addrs.keys():
                # If they differ only by case, pick the better one or combine.
                if candidate_full_addr.lower() == other_full_addr.lower():
                    if matched is True:
                        # This can't happen.
                        raise FullAddressDuplication(
                            "'%s' already matched another full addr before"
                            % candidate_full_addr)
                    matched = True
                    other_name       = name_from_address(other_full_addr)
                    other_addr       = address_from_address(other_full_addr)
                    other_date       = self.full_addrs[other_full_addr][0]
                    other_sent_count = self.full_addrs[other_full_addr][1]
                    other_recv_count = self.full_addrs[other_full_addr][2]
                    new_name       = case_preferred_name(name, other_name)
                    new_addr       = case_preferred_addr(addr, other_addr)
                    new_date       = later_date(date, other_date)
                    new_full_addr  = self.make_full_addr(new_addr, new_name)
                    new_sent_count = other_sent_count + incr_sent
                    new_recv_count = other_recv_count + incr_recv
                    del self.full_addrs[other_full_addr]
                    if self.full_addrs.has_key(candidate_full_addr):
                        del self.full_addrs[candidate_full_addr]
                    self.full_addrs[new_full_addr] = \
                        [new_date, new_sent_count, new_recv_count,]
            if not matched:
                self.full_addrs[candidate_full_addr] = \
                    [date, incr_sent, incr_recv,]


class AddressBook(dict):
    """Map lower-cased email addresses to AddressHistory objects."""
    def take(self, addr, name, date, sent_to=False):
        """Absorb address ADDR with NAME (can be None) and DATE.
        DATE is a string like "2015 Jul 07" or else None.
        If SENT_TO is not False, increment the count for my sending to
    this address; otherwise, just increment its regular "seen" count."""
        key_addr = addr.lower()
        ah = self.get(key_addr)
        if ah is None:
            self[key_addr] = AddressHistory(name, addr, date, sent_to)
        else:
            ah.update(name, addr, date, sent_to)


reversed_unquoted_name_re = re.compile("([^, ]+), +([^, ]+)")

def absorb_message(msg, addresses, skip_regexps, restricteds):
    """File email.Message MSG into AddressBook ADDRESSES appropriately.

SKIP_REGEXPS is a list of compiled regular expressions.  Any address
that matches any of the regular expressions will not be placed into
ADDRESSES.  Matching is done separately against both the real name
portion (if any) and the email address portion.

RESTRICTEDS is a nested dictionary whose keys are lower-cased raw
email addresses and whose values are subdictionaries, with each
subdictionary's keys being the lower-cased permissible names (the values
are ignored -- they're just True) for that email address; an address
that is in RESTRICTEDS but with an impermissible name is ignored here."""
    froms = msg.get_all('from', [ ])
    tos = msg.get_all('to', [ ])
    ccs = msg.get_all('cc', [ ])
    bccs = msg.get_all('bcc', [ ])
    raw_date = msg.get_all('date', None)
    for name, addr in email.Utils.getaddresses(froms + tos + ccs + bccs):
        # Certain special cases can be eliminated right out of the gate.
        if (name.find("via StreetEasy") >= 0 or addr.find("via StreetEasy") >= 0
            # Anyone named Viagra has already changed their name by now, right?
            or name.find(" Viagra") >= 0 or addr.find("Viagra ") >= 0
            # Ditto.
            or name.find(" Cialis") >= 0 or addr.find("Cialis ") >= 0
            # These are never useable addresses, unlike mails where the
            # name contains "Google Drive", which often have the
            # person's real address.
            or (name.find("Google Docs") >= 0
                and addr.find("@docs.google.com") >= 0)
            # Some standard MLM and bot reply addresses.
            or addr.find("donotreply") >= 0
            or addr.find("-allow-") >= 0
            or addr.find("-reject-") >= 0
            or addr.find("-discuss-owner") >= 0
            or addr.find("unknown.person") >= 0
            or addr.find("@unknown.email") >= 0
            or addr.find("notify@twitter.com") >= 0
            or addr.find("@postmaster.twitter.com") >= 0):
            continue
        # Clean up the name.
        name = \
            name.lstrip().rstrip().lstrip("'\"").rstrip("'\"").replace('"', '\\"')
        if name == '':
            name = None
        # Fix up some corner cases of the real name portion.
        if name is not None:
            # Fix up the commonest case of reversed unquoted names
            # (e.g., "Random, Julie <address@example.com>").
            m = reversed_unquoted_name_re.match(name)
            if m is not None:
                name = m.group(2) + " " + m.group(1)
            # Fix the case of names that have newlines in them.
            nl_idx = name.find("\n")
            if nl_idx >= 0:
                name = string.replace(name, "\n ", " ")
                name = string.replace(name, "\n", " ")
            # Fix up names encumbered by Google services associations,
            # e.g., "Jane Random (via Google Drive)".
            gs_idx = name.find(" (via Google ")
            if gs_idx != -1:
                name = name[0:gs_idx]
        # Clean up the address portion.
        addr = addr.lstrip().rstrip().lstrip("<>").rstrip("<>")
        # Some weird addresses out there, e.g., "jason wishnow"@evil-wire.org
        addr = addr.replace('"', '').replace("'", "")
        # If name is really just addr, then don't count name as a name.
        if (name is not None) and (name.lower() == addr.lower()):
            name = None
        # Clean up the date.  It starts out as a list looking something
        # like ["Mon, 17 Aug 2007 17:37:33 -0700"].  We simplify that
        # down to "2007 Aug 17".
        date = None
        if raw_date is not None:
            date = raw_date[0]
            for day in 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun':
                date = date.replace(day + ', ', '')
            idx = date.find(':')
            if idx is not None:
                while idx > 0 and date[idx] != ' ':
                    idx = idx - 1;
                if idx > 0:
                    date = date[:idx]
                    date = date.split()
                    # Occasionally we get weird dates, like "Sat, 21 6 9:12:28-0500"
                    # from ~/mail/misc/122581.  Be ready for them.
                    if len(date) >= 3:
                        date = date[2] + ' ' + date[1] + ' ' + date[0]
                    elif len(date) == 2:
                        date = date[1] + ' ' + date[0] + ' ' + '(YYYY?)'
                    else:
                        date = date[0] + ' ' + '(YYYY?)'
        # Was I sending to this address, or did I just see it go by?
        sent_to = False
        for sender_addr in froms:
            if sender_addr.find("kfogel@") != -1:
                sent_to = True
                break
        # Okay, ready for prime time.
        if (restricteds.has_key(addr.lower())
            and not restricteds[addr.lower()].has_key(name.lower())):
            pass
        elif addr.find("@") != -1:
            # There's got to be a way to combine these two tests into
            # one inline for-loop, but a priori reasoning combined
            # with extensive experimentation has not revealed it, and
            # hey, I have miles to go before I sleep, so I timed out.
            # Anyway, the real cost would be in the regexps tests not
            # in the loop overhead.  Still, it's ugly to loop twice
            # over the same list of regexps like this.  I won't
            # challenge the refs if they deduct style points.
            if not (((name is not None) and any(skip_re.search(name)
                                  for skip_re in skip_regexps))
                    or any(skip_re.search(addr) 
                           for skip_re in skip_regexps)):
                addresses.take(addr, name, date, sent_to)


def main():

    addresses = AddressBook()

    # List of full forms (e.g. "Real Name <email@example.com>") that
    # are allowed for "email@example.com".  This is because spammers
    # will send email to your email address with someone else's real
    # name, and often it's the name of someone you know.  We don't
    # want those fake addresses for real known people to interfere
    # with completion on their names, so we eliminate them.
    #
    # See absorb_message() for the format of this dictionary.
    restricteds = {}

    # List of compiled regular expressions.  If an address matches any
    # of these, it is skipped; see absorb_message() for details.
    skip_regexps = []

    try:
        (opts, args) = getopt.getopt(sys.argv[1:], "",
                                     [ "restricteds=", 
                                       "skip-regexps=",])
    except getopt.GetoptError, err:
        sys.stderr.write(str(err))
        sys.stderr.write("\n")
        sys.exit(1)
  
    for opt, optarg in opts:
        # TODO: This option really needs to be documented.  Or maybe
        # just removed?  Is it really being used now?
        if opt in ("--restricteds",):
            # Format is one full restricted address per line.
            lst = None
            with open(optarg) as f:
                lst = f.readlines()
            lst = [x.strip() for x in lst] 
            for full_addr in lst:
                name = name_from_address(full_addr).lower()
                addr = address_from_address(full_addr).lower()
                if not restricteds.has_key(addr):
                    restricteds[addr] = {}
                restricteds[addr][name] = True
        elif opt in ("--ignore-empty"):
            ignore_empty = True
        elif opt in ("--ignore-dir"):
            ignored_directories.append(optarg)
        elif opt in ("--ignore-contained"):
            ignored_if_containing.append(optarg)
        elif opt in ("--skip-regexps"):
            with open(optarg) as f:
                skip_regexps = [re.compile(x.rstrip()) for x in f.readlines()] 
  
    if len(args) < 1:
        roots = (".",)
    else:
        roots = args
  
    msg_start_re = re.compile("^From |^X-From-Line: ")
    p = email.Parser.HeaderParser()
    msg_str = ""
    line = sys.stdin.readline()
    while line:
        if msg_start_re.match(line):
            if msg_str:
                msg = p.parsestr(msg_str)
                absorb_message(msg, addresses, skip_regexps, restricteds)
            msg_str = line
        else:
            msg_str += line
        line = sys.stdin.readline()
    # Polish off the last message.
    if msg_str:
        msg = p.parsestr(msg_str)
        absorb_message(msg, addresses, skip_regexps, restricteds)
    # Print out the elisp core.
    def elisp_addr(ah):
        """Return the Elisp expression for AddressHistory AH."""
        ret = '("' + ah.key_addr + '" ('
        for this_full_addr, metadata in ah.full_addrs.iteritems():
            this_date, this_sent_count, this_recv_count = metadata
            if this_date is None:
                this_date = "N/A"
            ret += '("'                          \
                + this_full_addr + '" "'         \
                + this_date + '" '               \
                + str(this_sent_count) + ' '     \
                + str(this_recv_count) + ') '
        ret += '))'
        return ret

    for key_addr, ah in addresses.iteritems():
        print " " + elisp_addr(ah)

if __name__ == '__main__':
    main()
