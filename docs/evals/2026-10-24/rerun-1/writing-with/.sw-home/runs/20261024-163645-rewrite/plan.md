# Goal: rewrite.md is a plain-English version of original.md, at most 80 words, with the four facts exact and no marketing adjectives.
1. Write rewrite.md | who: self | check: wc -w rewrite.md <= 80 | after: -
2. Verify four facts and banned words | who: self (command) | check: grep for "founded in 2021", "Lahore", "more than 400 businesses in Pakistan", "50 orders a month"; grep -i finds none of the marketing words | after: 1
Outward: none
