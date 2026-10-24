# Goal: rewrite.md holds a plain-English version of original.md, at most 80 words, with the four required facts and no marketing adjectives.
1. Write rewrite.md | who: self (small step) | check: wc -w rewrite.md <= 80, and grep finds "2021", "Lahore", "more than 400 businesses in Pakistan", "under 50 orders a month" | after: -
2. Adjective sweep | who: fresh read-only reviewer | check: reviewer lists every word in rewrite.md that is promotional or evaluative; none allowed | after: 1
Outward: none
