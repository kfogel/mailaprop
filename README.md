mailaprop: modern autofill for email addresses in GNU Emacs.
============================================================

*TODO (2018-01-10): This documentation is a work in progress.*

Overview
--------

Mailaprop provides popup-style email address completion when composing
mail in Emacs.  Here's a [video of mailaprop in
action](mailaprop-example-session.webm) (click through and then click
"View Raw").

As you start typing an address, a popup window offers the possible
completions so far, prioritized according to how often the addresses
appear in your email; sent-to addresses are weighted more highly than
received-from addresses.  Each address also shows the date it was last
interacted with (sent to or received from), and its mailaprop score.

Use arrow keys to navigate up and down the candidate addresses, or
type more letters to narrow the list further.  Once you've got the
address you want, hit Return to insert that address into the email
header.

This is basically the same autofill behavior you're probably used to
having in your browser when you interact with the sorts of online
services that send proprietary Javascript to your tabs.  Unlike them,
however, this package is entirely free software and operates on data
that is all stored locally.  You shouldn't need to hand your social
graph to billionaires just to get decent autofill behavior.

Speaking of which, you don't have to use any proprietary Javascript to
interact with this project.  You can use plain git to clone the
repository from GitHub at https://github.com/kfogel/mailaprop.git, and
I'll happily take bug reports by email instead of via the GitHub issue
tracker: kfogel {_AT_} red-bean.com.

How long does it take to set up?
--------------------------------

Probably an hour or two, if you are experienced with basic scripting
and are comfortable making minor changes to your ~/.emacs (or wherever
you keep your Emacs initialization code).

If you're new to this kind of thing, it could take a day or more to
set up.  If neither of these paragraphs made sense to you, it could
take an arbitrary amount of time, and you might want to step slowly
away from the computer to reconsider various choices in your life.

What about BBDB?  Doesn't it already do this?
---------------------------------------------

Does [BBDB](https://www.emacswiki.org/emacs/BbdbMode) offer
popup-style autofill these days?  It might.  It's been a long time
since I used BBDB.  Back when I last did, a decade or five ago, email
address completion wasn't working.  Maybe I failed to run some
initialization function, or mis-installed BBDB, or whatever.  Who
knows?  It's BBDB.

BBDB later went dormant, and then came alive again, and is now
actively maintained, so perhaps my libels are outdated.  See the
[development page](http://savannah.nongnu.org/projects/bbdb/) and
[commit logs](http://git.savannah.nongnu.org/cgit/bbdb.git/log/) for
more.

Anyway, it's too late.  By now I'm in too deep to get out.

Installation instructions.
--------------------------

First, a high-level view:

You run a shell script (build-address-list.sh), which invokes a Python
script (mailaprop.py) that ingests various mbox files supplied by you.
You customize the shell script to find whatever input files you want.
As long as they're in mbox format, and have desirable email addresses
waiting to be harvested in the message headers, they should be fine.

The result of this is a file, 'email-addresses.eld' -- that's the
completion database.

Your .emacs loads mailaprop.el, and runs some mailaprop functions that
inhale that file.  You'll also adjust Emacs mail-mode and message-mode
so that when you start typing in a header that expects email
addresses, you get the popup-style autofill behavior offering the possible
completions so far, prioritized according to how often the addresses
appear in your email (with sent-to addresses weighted more highly than
received-from).

Details:

*TODO: The rest of these instructions still need some work.*

Modify build-address-list.sh as needed; comments in that file will
explain how.  (You may eventually want to invoke it from a cron job so
it runs daily to rebuild your completion database, since presumbably
your input files will always be accumulating new addresses.)

Run it.  Congratulations, you've got a file full of email addresses!

Grab my .emacs (http://svn.red-bean.com/repos/kfogel/trunk/.emacs) and
search for "mailaprop".  You may want to write a custom
`mailaprop-skip-address-fn` as I did.

TODO: document setting `mailaprop-address-file`

TODO: document order of things in .emacs (but maybe fix mailaprop.el
so that it's less sensitive to that order).

TODO: update `mail-mode-hook` and `message-mode-hook`.

TODO: document how each email address must be on its own line

Finding boundaries between email addresses on the same line turns out
to be surprisingly non-trivial, so I decided to punt on the problem.
Instead, you can only complete an address that is on its own line or
on the same line as the header name.  Thus, both of these addresses
could have been autofilled:

        To: J. Random <jrandom@jrandom.com>,
            Victoria O'Hara <vickyh@foo.bar>

but below, the second one could not have been autofilled:

        To: J. Random <jrandom@jrandom.com>, Victoria O'Hara <vickyh@foo.bar>
