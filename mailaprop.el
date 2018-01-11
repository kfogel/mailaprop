;;;; Mailaprop: a custom completion system for my email contacts.
;;;
;;; Copyright (C) 2007-2018  Karl Fogel
;;; 
;;; This program is free software: you can redistribute it and/or modify
;;; it under the terms of the GNU Affero General Public License as published by
;;; the Free Software Foundation, either version 3 of the License, or
;;; (at your option) any later version.
;;; 
;;; This program is distributed in the hope that it will be useful,
;;; but WITHOUT ANY WARRANTY; without even the implied warranty of
;;; MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
;;; GNU Affero General Public License for more details.
;;; 
;;; You should have received a copy of the GNU Affero General Public License
;;; along with this program.  If not, see <http://www.gnu.org/licenses/>.

;; TODO: 
;;
;;  - Finish the documentation.
;;  - Maybe get out of company-mode after leaving mail headers.
;;
;; Resources referred to while developing this:
;; 
;;  - https://www.emacswiki.org/emacs/CompanyMode
;;  - https://github.com/company-mode/company-mode/wiki/Writing-backends
;;  - http://sixty-north.com/blog/writing-the-simplest-emacs-company-mode-backend

(require 'cl-lib)

;; TODO: This isn't part of standard Emacs yet, right?  I may have to
;; finally learn how to use ELPA, so I can document for others how to
;; get company-mode.  https://github.com/company-mode/company-mode/ is
;; where I get it from, for what it's worth, and I load it with this:
;;
;;   (let* ((local-company (expand-file-name "~/src/company-mode")))
;;     (when (file-exists-p local-company)
;;       (add-to-list 'load-path local-company)
;;       (require 'company)))
;;
(require 'company)

(defvar mailaprop-address-file
  (expand-file-name "~/private/mailaprop/email-addresses.eld")
  "*File created by mailaprop.py et al, containing completable addresses.")

(defun mailaprop-read-sexp-from-file (file)
  "Read an sexp from FILE, returning nil if FILE does not exist."
  (if (file-exists-p file)
      (save-excursion
        (let* ((large-file-warning-threshold nil)
               (buf (find-file-noselect file)))
          (set-buffer buf)
          (goto-char (point-min))
          (prog1
              (read (current-buffer))
            (kill-buffer (current-buffer)))))
    '()))

(defun mailaprop-inhale-addresses ()
  "Read and return the lisp expression in `mailaprop-address-file'."
  (mailaprop-read-sexp-from-file mailaprop-address-file))

(defvar mailaprop-addresses (mailaprop-inhale-addresses)
  "All email addresses, with their most-recently-seen dates and their scores.  
Each element is of the form (ADDRESS DATE SCORE), where ADDRESS is a
string (often \"Full Name <address@example.com>\"), DATE is a string
(like \"1970 Jan 01\"), and SCORE is an integer.
Normally, only `mailaprop-load-addresses' creates this list.")

;; Accessors for the address-entry elements in `mailaprop-addresses'.
;; (This kind of thing is what CL objects would be for, I guess, but
;; for now we'll do it with accessor macros and call it a day.)
(defmacro mailaprop-ae-get-addr (fa)
  "Return the address part of FullAddress FA."
  `(nth 0 ,fa))

(defmacro mailaprop-ae-get-date (fa)
  "Return the date part of FullAddress FA."
  `(nth 1 ,fa))

(defmacro mailaprop-ae-get-score (fa)
  "Return the score part of FullAddress FA."
  `(nth 2 ,fa))

(defconst mailaprop-date-dict nil
  "Hash table mapping addresses to date strings, for annotations.
It is initialized and populated only by `mailaprop-digest-address-data'.")

(defconst mailaprop-score-dict nil
  "Hash table mapping addresses to score strings, for annotations.
It is initialized and populated only by `mailaprop-digest-address-data'.")

(defconst mailaprop-memoize-dict (make-hash-table :test 'equal)
  "Dictionary mapping candidate substrings to lists of addresses.
Each list contains all the addresses that `mailaprop-get-candidates'
would return for that candidate substring.")

(defvar mailaprop-skip-address-fn nil
  "*If non-nil, a user-defined function to decide whether to keep an address.
When mailaprop loads email addresses in `mailaprop-digest-raw-addresses',
this function is called once per address, with these arguments;

  GROUP-KEY-ADDR: (string) The all lower-case email address that all
    the addresses in this group have in common.  Note that this
    address is always present as a member of the group, even if
    no other addresses with full names are present.  In other
    words, at least once per group, the function will be called
    with GROUP-KEY-ADDR and ADDR having the same value.

  GROUP-SIZE: (integer) The number of addresses in this group.  For
    example, if a group has \"Jane Random <jrandom@example.com>\"
    and \"jrandom@example.com\" as its members, the group's size
    is 2.  No group has a size lower than 1.

  THIS-ADDR: (string) The address currently being considered.  For
    example, GROUP-KEY-ADDR might be \"<jrandom@example.com>\" while
    THIS-ADDR is \"Jane Random <jrandom@example.com>\".")

(defvar mailaprop-skip-addresses nil
  "*A list of regular expressions to indicate what addresses to skip.
If the combined address (like \"Jane Random <jrandom@example.com>\" if
real name portion is present, or else \"jrandom@example.com\")
then that address will not be included in the completion set.

See `mailaprop-skip-address-fn' for a more general mechanism for
choosing which addresses to skip.  Everything provided by this list
could be implemented in a custom `mailaprop-skip-address-fn'; this
list is just a convenience that handles the majority of cases.")

(defun mailaprop-digest-raw-addresses (raw-addresses)
  "Digest RAW-ADDRESSES to create `mailaprop-addresses'.
RAW-ADDRESSES is a list as read from `mailaprop-address-file'."
  ;; Populate (or reset and repopulate) the date dictionary.
  (setq mailaprop-date-dict
        (make-hash-table :test 'equal :size (length raw-addresses)))
  (setq mailaprop-score-dict
        (make-hash-table :test 'equal :size (length raw-addresses)))
  (let ((lst ())
        (name-bonus (length raw-addresses)))
    (dolist (group raw-addresses)
      (let ((group-key-addr (car group))
            (group-size (length (car (cdr group)))))
        (dolist (addr-entry (car (cdr group)))
          (let ((addr (car addr-entry)))
            (unless (or 
                     ;; If this group has multiple versions of the address, and
                     ;; the address we're looking at is exactly the same as the
                     ;; group's key address, then there is no point including
                     ;; this address -- we know better versions are available.
                     (and (> group-size 1)
                          (string-equal group-key-addr addr))
                     ;; If the user says to skip it, then skip it.
                     (catch 'matched
                       (dolist (re mailaprop-skip-addresses)
                         (when (string-match-p re addr)
                           (throw 'matched t))))
                     (funcall mailaprop-skip-address-fn 
                              group-key-addr group-size addr))
              (let* ((date (nth 1 addr-entry))
                     (sent (nth 2 addr-entry))
                     (recv (nth 3 addr-entry))
                     (score (+ (* sent 2) recv)))
                ;; A sent-to count counts twice as much as a received count.
                (setq lst (cons (list addr date score) lst))
                (puthash addr date mailaprop-date-dict)
                (puthash addr score mailaprop-score-dict))))
          (setq mailaprop-addresses lst))))))

(defun mailaprop-load-addresses ()
  "Load (or reload) the email address completion table."
  (interactive)
  (mailaprop-digest-raw-addresses (mailaprop-inhale-addresses))
  (clrhash mailaprop-memoize-dict))
(defalias 'mailaprop-reload-addresses 'mailaprop-load-addresses)

(when (file-exists-p mailaprop-address-file)
  (mailaprop-load-addresses)) ; load the data for this session

(defun mailaprop-complete-address ()
  "TAB-complete an email address on a line by itself before point.
Ordinarily, you wouldn't use this, because you'd be using the
`company-mode'-style tooltip completion instead.  But maybe for
some reason you're old-school and prefer to do TAB-based completion.
In that case, it should still work; hence this function."
  (interactive "*")
  (let* ((completion-ignore-case t)
         (opoint (point))
         (bpoint (save-excursion
                   (beginning-of-line)
                   (when (looking-at "^\\s-+$")
                     (error
                      "Completing here may cause an infinite binary loop"))
                   (re-search-forward "\\s-")
                   (re-search-forward "\\S-")
                   (forward-char -1)
                   (point)))
         (prefix (buffer-substring bpoint opoint))
         (attempt (try-completion prefix mailaprop-addresses))
         (completion (mailaprop-ae-get-addr
                      (assoc attempt mailaprop-addresses))))
    (goto-char opoint)
    (when (not completion)
      (setq completion 
            (mailaprop-ae-get-addr 
             (assoc (completing-read "" mailaprop-addresses nil t prefix)
                    mailaprop-addresses))))
    (delete-region bpoint opoint)
    (goto-char bpoint)
    (insert completion)))

(defun mailaprop-handle-tab ()
  "Invoke `mailaprop-complete-address' if in an email header."
  (interactive "*")
  (require 'mailabbrev)
  (if (mail-abbrev-in-expansion-header-p)
      (mailaprop-complete-address)
    (indent-for-tab-command)))


(defun mailaprop-get-candidates (substr)
  "Return a list of candidate completions for SUBSTR."
  (or (gethash substr mailaprop-memoize-dict nil)
      ;; If it wasn't memoized, then build, memoize, and return it.
      (let ((lst ())
            (case-fold-search t))
        (dolist (addr-entry mailaprop-addresses)
          (let ((score (mailaprop-ae-get-score addr-entry)))
            (let ((date (mailaprop-ae-get-date addr-entry)))
              (when (string-match-p
                     (regexp-quote substr) (mailaprop-ae-get-addr addr-entry))
                (setq lst (cons (list (mailaprop-ae-get-addr addr-entry)
                                      date
                                      score)
                                lst))))))
        (puthash substr
                 (mapcar (lambda (elt) (car elt))
                         (sort lst
                               (lambda (a b)
                                 (cond
                                  ;; We prefer any address that has a real-name
                                  ;; component over one that doesn't.
                                  ((and (string-match-p 
                                         " " (mailaprop-ae-get-addr a))
                                        (not (string-match-p
                                              " " (mailaprop-ae-get-addr b))))
                                   t)
                                  ((and (string-match-p
                                         " " (mailaprop-ae-get-addr b))
                                        (not (string-match-p
                                              " " (mailaprop-ae-get-addr a))))
                                   nil)                     
                                  ((> (mailaprop-ae-get-score a)
                                      (mailaprop-ae-get-score b)) 
                                   t)
                                  ((> (mailaprop-ae-get-score b)
                                      (mailaprop-ae-get-score a))
                                   nil)
                                  ;; Just kluge dates for now, if
                                  ;; scores are equal.  We could do a
                                  ;; real date comparison; in fact,
                                  ;; the Python code implements that
                                  ;; (bin/mailaprop/mailaprop.py).
                                  ;; But by the time you get down to
                                  ;; these details in the sort, it
                                  ;; doesn't really matter anymore.
                                  ;; We could frankly just return t;
                                  ;; but since it's so cheap to at
                                  ;; least sort on the year, we do.
                                  ((string-greaterp (mailaprop-ae-get-date a)
                                                    (mailaprop-ae-get-date b))
                                   t)
                                  (t
                                   nil)))))
                 mailaprop-memoize-dict))))

(defun mailaprop-find-date (addr)
  "Return the date (as a string) corresponding to ADDR.
If there is no date corresponding to ADDR, return the empty string."
  (or (gethash addr mailaprop-date-dict) ""))

(defun mailaprop-find-score (addr)
  "Return the score (as a number) corresponding to ADDR.
If there is score corresponding to ADDR, return zero."
  (or (gethash addr mailaprop-score-dict) 0))

(defun company-mailaprop-backend (command &optional arg &rest ignored)
  (interactive (list 'interactive))
  (cl-case command
    (interactive      (company-begin-backend 'company-mailaprop-backend))
    (prefix           (when (mail-abbrev-in-expansion-header-p)
                        (cons (company-grab-line
                               "^\\(\\s-+\\|to:\\s-+\\|cc:\\s-+\\|bcc:\\s-+\\)\\(.*\\)" 
                               2)
                              t)))
    (candidates       (when (> (length arg) 0)
                        ;; Note that this treats arg not as a prefix,
                        ;; but as a substring that can appear anywhere
                        ;; in the address.
                        (mailaprop-get-candidates arg)))
    (post-completion  nil)
    (annotation       (concat 
                       " | " (mailaprop-find-date arg)
                       " | (" (number-to-string (mailaprop-find-score arg))
                       ")"))
    (sorted           t)
    (ignore-case      t)
    (no-cache         t)
    ))

(when (boundp 'company-backends)
  (add-to-list 'company-backends 'company-mailaprop-backend))
