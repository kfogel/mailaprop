mailaprop: modern autofill for email addresses in GNU Emacs.
============================================================

Overview
--------

Mailaprop provides popup-style email address completion when composing
mail in Emacs:

<p align="center">
  <a href="https://player.vimeo.com/video/250746180">
    <img alt="Mailaprop Example Session" src="mailaprop-example-session.png" width="75%" />
  </a>
</p>

As you start typing an address, a popup window offers the possible
completions so far, prioritized according to how often the addresses
appear in your email; sent-to addresses are weighted more highly than
received-from addresses.  Each address also shows the date it was last
interacted with (sent to or received from), and its mailaprop score.

Almost always, after you've typed a few letters the top candidate
address will be the one you want -- you just hit Return to choose it.
Otherwise, you can use the arrow keys to navigate up and down the
list, or type more letters to narrow to fewer candidates.

This is basically the same autofill feature you're probably used to
having in your browser when you interact with the sorts of online
services that send proprietary Javascript to your tabs.  Unlike them,
however, this package is entirely free software and operates on data
that is all stored locally.  You shouldn't need to hand over your
social graph to billionaires just to get decent autofill behavior.

Speaking of which, you don't have to use any proprietary Javascript to
interact with this project.  You can use plain git to clone the
repository from GitHub at https://github.com/kfogel/mailaprop.git, and
I'll happily take bug reports by email instead of via the GitHub issue
tracker: kfogel {_AT_} red-bean.com.

How long does it take to set up?
--------------------------------

About an hour, if you are experienced with basic scripting and are
comfortable making minor changes to your ~/.emacs (or wherever you
keep your Emacs initialization code).

If you're new to this kind of thing, it could take a day or more to
set up.  If neither of these paragraphs made sense to you, then it
could take an arbitrary amount of time, and you might want to step
slowly away from the computer to reconsider various choices in your
life.

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

You run a shell script (`build-address-list.sh`), which invokes a
Python script (`mailaprop.py`) that ingests various mbox files.  You
told `mailaprop.py` where to find those mbox files by making light
edits to `build-address-list.sh`.

There can be as many input files as you want.  As long as they're in
mbox format, and have email addresses waiting to be harvested in their
message headers, they should work.

The result of the above is a file, 'mailaprop-addresses.eld' -- that's
the completion database.  Your .emacs loads `mailaprop.el`, and runs
some mailaprop functions that inhale 'mailaprop-addresses.eld'.

You'll also add some hooks to `mail-mode-hooks` and
`message-mode-hooks` so that when you are in a message composition
buffer and you start typing in the `To:`, `CC:`, or `BCC:` header, you
get the popup-style autofill behavior.

Details:

*TODO (2018-01-12): The rest of these instructions still need some work.*

Modify `build-address-list.sh` as needed; comments in that file will
explain how.  (You may eventually want to invoke it from a cron job so
it runs daily to rebuild your completion database, since presumbably
your input files will always be accumulating new addresses.)

Run it.  Congratulations, you've got a file full of email addresses!

Grab my [.emacs](http://svn.red-bean.com/repos/kfogel/trunk/.emacs)
and search for "mailaprop".  You may want to write a custom
`mailaprop-skip-address-fn` as I did.

TODO: give some idea of how long mailaprop.py will take to run

TODO: document setting `mailaprop-address-file`

TODO: document order of things in .emacs (but maybe also fix
`mailaprop.el` so that it's less sensitive to that order).

TODO: document what to do to `mail-mode-hook` and `message-mode-hook`.

TODO: document how each email address must be on its own line in the
      composition headers.

Finding boundaries between email addresses on the same line turns out
to be surprisingly non-trivial, so I decided to punt on the problem.
Instead, you can only complete an address that is on its own line or
on the same line as the header name.  Thus, both of these addresses
could have been autofilled:

        To: J. Random <jrandom@jrandom.com>,
            Victoria O'Hara <vickyh@foo.bar>

but below, the second one could not have been autofilled:

        To: J. Random <jrandom@jrandom.com>, Victoria O'Hara <vickyh@foo.bar>
