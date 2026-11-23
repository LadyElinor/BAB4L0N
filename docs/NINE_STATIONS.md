# Nine Stations in remedy review

An operator can read a remedy case through the order used in [The Nine Stations](https://nine-stations.owonm.chatgpt.site/). The civic interpretation comes from [The Living Commonwealth](https://nine-stations.owonm.chatgpt.site/the-living-commonwealth.html). [The Practice of Return](https://nine-stations.owonm.chatgpt.site/practice-of-return.html) brings the reader back to an ordinary responsibility. Source edition 12, revision 41f434ef41a230c45f6e4e5a7f9087ecde3af822. The manuscript sets its own sequence. The questions in Babalon are an application written for operators. The spiritual meanings belong in their original setting.

Run from the repository root:

```sh
python -m babalon remedy-review tests/fixtures/commonwealth/owed-assistance.json --as-of 6 --nine-stations
```

Read the nine questions in order or revisit any of them. Each appears next to structured observations already available in the ordinary review. A question calls for judgment from the reviewer. There is no grade for the reviewer or the person owed a remedy.

For the example, Wara’ asks what use of the person's account they agreed to. The record says they declined further contact. Rida asks how the institution can carry out its existing duty within that limit. The practice of return assigns the missing delivery evidence to the payments office and the outstanding finding to the review office. Adding `--register tests/fixtures/commonwealth/receiving-register.json` establishes a recorded credit of 100 units. The delivery question drops out while the outstanding finding remains. How the person experienced the remedy is a separate question. Their choice to leave is sufficient on its own.

The switch adds a view to the printed local report. Evidence, exit status, contact permissions and execution authority continue to come from the existing review. The view uses record IDs and structured states. Its prompts remain with the operator. A future blinded comparison could test whether reviewers identify more unsupported closure decisions or overlooked duties in the same time.
