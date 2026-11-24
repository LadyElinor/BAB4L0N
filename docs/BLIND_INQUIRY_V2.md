# Blinded inquiry collection v2

Use v2 for new collections. It accepts the worksheet, method key, answers and individual review formats from [v1](BLIND_INQUIRY.md). The historical collector checks that submitted records agree internally. V2 additionally requires a separately retained digest for a closed custody register. The register binds the worksheet, method key, interpreter's answers, full named reviewer roster and every review. Record digests use v1 canonical JSON, so whitespace and object key order may change. List order and all field values are committed.

## Before unblinding

1. Before retrieval, follow v1's selection and freeze procedure. Record the Git revision used for both stages, the interpreter, the full reviewer roster, exposures and custody arrangements outside the submission directory. Use unseen materials for an independent evaluation. Deposit the freeze digest before running. At the run, retain the worksheet and key digests, keep the key private and give the interpreter only the worksheet.
2. The interpreter completes the v1 answer file. Run the following command and deposit its output with the custodian before reviewers receive the answers. In the examples, uppercase arguments stand for digests retrieved from custody.

   ```sh
   python scripts/blind_inquiry.py seal-answers worksheet.json answers.json
   ```

3. Give each reviewer the worksheet, committed answers, retained answer digest and precommitted rubric. Each reviews in isolation and uses this command on their own file. It checks the worksheet and answer links and prints the canonical digest of the **entire** review, including the reviewer ID, judgments, citations, reasons and unanswered questions. Each reviewer deposits their ID and digest directly with the custodian. Other reviewers' files, judgments and the method key stay private.

   ```sh
   python scripts/blind_inquiry_v2.py seal-review worksheet.json answers.json ANSWER_DIGEST review-a.json
   ```

4. The custodian checks the worksheet digest against the run record. Match every direct deposit to the preregistered roster. If anyone withdraws or a deposit is missing, record the incomplete run and stop. Close the register using the original run and answer digests and the separately received reviewer digests. Supply one `--review` for every reviewer. This command takes no answer files, review files or private key. Retain the printed register digest in a dated, independent record before authorizing unblinding. Keep the custody receipts and release order for audit.

   ```sh
   python scripts/blind_inquiry_v2.py close-register worksheet.json KEY_DIGEST ANSWER_DIGEST register.json \
     --review reviewer-a REVIEW_A_DIGEST --review reviewer-b REVIEW_B_DIGEST
   ```

## Collection and interpretation

Retrieve the register digest and original freeze digest from the independent record. Use the register and the submitted files as inputs. The collector rejects a changed register, checks the answers against their deposit, and requires exactly one matching review for every registered ID before reading the private key. It then applies v1's key, rubric, worksheet and substantive row checks and writes a new report. A failed verification produces no report. Keep the individual review files for later verification.

```sh
python scripts/blind_inquiry_v2.py collect worksheet.json custodian-only.json answers.json rubric.txt \
  freeze.json FREEZE_DIGEST register.json REGISTER_DIGEST result.json review-a.json review-b.json
```

The report retains each judgment and all per-dimension disagreements. The register digest identifies the evidence for the collection, including the collector and protocol document hashes at closure. The report keeps `promotion_eligible: false` and `status: NOT_PROMOTED`.

**What the check establishes.** Given an authentic retained digest, a successful collection verifies that the submitted records match the committed contents. Reviewer identity, independence, prior exposure, completeness of the initial roster and the timing of deposits and key release require external evidence. Keep the original log under independent control. A register created retrospectively from a submission cannot establish pre-unblinding custody.

**Historical scope.** V1 freezes and rehearsal reports remain reproducible on their original protocol. Existing runs without contemporaneous deposits retain their original evidence status. The exposed rehearsal found 12 of 16 designated targets for shared-gap and 13 of 16 each for keyword and BM25, using 29 matched passage inspections per method. These are retrieval counts. Human judgments in the regression tests below are synthetic.

Run the collection tests with `python -m unittest discover -s tests -p 'test_blind_inquiry_v2.py' -v`.
