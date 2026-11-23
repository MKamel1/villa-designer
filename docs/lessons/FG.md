# FG lessons

## 1. A generated outline passed as a species scan (caught before hand-back)
* **What:** the first label logic compared the *bank's scientific name* with the species. The synthetic palmate banks (our own Fatsia/grape outline over a
  Colocasia surface) had been named "Fatsia japonica (outline only...)", so `fidelity` came out `species` for fatsia and grape.
* **Why missed:** the bank record had one name field serving two purposes (what the surface was scanned from, what the outline imitates); the tests I had
  checked that labels were present, not that they could not over-claim.
* **Guard:** `test_generated_outline_is_never_species_fidelity` and `test_only_the_species_whose_scan_it_is_is_species_fidelity` (only star jasmine may be
  `species`); `label_of` refuses `species` for any bank with `synthetic_outline`; `validate_label` refuses it again at the library boundary.

## 2. Dark scans multiplied into noise
* **What:** Megascans leaf albedos are very dark (mean sRGB ~15-50). A colour gain of ~10-190x in linear light turned JPEG noise and edge pixels of the
  synthetic crop into white/yellow flecks on fatsia and grape.
* **Why missed:** the first sheets were judged at 5 m crops where a speck is 1 px; the close-up row showed them.
* **Guard:** the sheets always include a close-up row; the synthetic surface is lifted to a mid green, clipped and median-filtered before use, so the per-species gain stays near 1. (No automatic speck check yet: open item.)

## 3. Sheets at fixed 35 mm made a 0.3 m plant 12 px wide
* **Guard:** sheet frames are cropped (render border) to 1.5x the plant; the 15 m row keeps the 5 m window so the plant is shown at 1/3 size, as seen at 15 m.
