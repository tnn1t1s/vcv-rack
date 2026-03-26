# SlimeChild Substation -- PolySeq (Polyrhythm Sequencer)

**Plugin:** `SlimeChild-Substation`  **Model:** `SlimeChild-Substation-PolySeq`

3-sequence polyrhythmic CV sequencer with 4 independent rhythmic dividers.

## Params

| ID    | Name      | Notes |
|-------|-----------|-------|
| 0-3   | A1-A4     | Sequence A step values [-1, 1] |
| 4-7   | B1-B4     | Sequence B step values |
| 8-11  | C1-C4     | Sequence C step values |
| 12-15 | DIV1-DIV4 | Rhythm dividers [1, 16] |
| 16-19 | DIV1_A-DIV4_A | Route divider N to sequence A (0/1) |
| 20-23 | DIV1_B-DIV4_B | Route divider N to sequence B |
| 24-27 | DIV1_C-DIV4_C | Route divider N to sequence C |
| 28-30 | RANGE_A/B/C | Output voltage range [0, 2] |
| 31    | SUM_MODE  | 0=last step, 1=sum dividers |
| 32    | RESET     | Reset button |
| 33    | NEXT      | Manual step button |
| 34    | STEPS     | Number of active steps [1, 8], default=4 |

## Inputs

| ID | Name  | Notes |
|----|-------|-------|
| 0  | CLOCK | Master clock |
| 1  | RESET | Reset trigger |
| 2  | DIV1  | CV for divider 1 rate |
| 3  | DIV2  | CV for divider 2 rate |
| 4  | DIV3  | CV for divider 3 rate |
| 5  | DIV4  | CV for divider 4 rate |

## Outputs

| ID | Name  | Notes |
|----|-------|-------|
| 0  | TRIG1 | Trigger from divider 1 |
| 1  | TRIG2 | Trigger from divider 2 |
| 2  | TRIG3 | Trigger from divider 3 |
| 3  | TRIG4 | Trigger from divider 4 |
| 4  | SEQ_A | Sequence A CV |
| 5  | SEQ_B | Sequence B CV |
| 6  | SEQ_C | Sequence C CV |

## Notes

- Each divider can route to any combination of A/B/C sequences via routing matrix params
- 3:4 polyrhythm example: DIV1=3 routed to A, DIV2=4 routed to B
- DIV input count and TRIG/SEQ output index order confirmed from manual; exact DIV CV behavior TBD
