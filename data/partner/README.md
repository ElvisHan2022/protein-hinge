# Partner Data Used For The Scientific Figure

These files are the small public processed CPJUMP1 outputs used by
`scripts/make_cell_perturbation_figure.py`.

Refresh commands:

```bash
curl -fsSLo data/partner/candidate_ranking.csv https://raw.githubusercontent.com/biobitworks/aws-biopharma/main/data/magicstudiobox/runs/primary/candidate_ranking.csv
curl -fsSLo data/partner/perturbation_state.json https://raw.githubusercontent.com/biobitworks/aws-biopharma/main/data/magicstudiobox/runs/primary/perturbation_state.json
curl -fsSLo data/partner/state_model.json https://raw.githubusercontent.com/biobitworks/aws-biopharma/main/data/magicstudiobox/runs/primary/state_model.json
curl -fsSLo data/partner/evaluation.json https://raw.githubusercontent.com/biobitworks/aws-biopharma/main/data/magicstudiobox/runs/primary/evaluation.json
```

Expected SHA-256 digests:

```text
candidate_ranking.csv      e93d3ce7526049c8904e36e6e1aeefc2558c38b3032c8c348342390d8cf30b51
evaluation.json            ede568677be5d45412f359153ebd60ada87b23ec93db6a33f9e836bce1bea62f
perturbation_state.json    c6fa95aaf2094767f613f6900f737a6cadc5e0b996b46ea83a3cfe7516bb1bf7
state_model.json           4028c343675f298ba3c91171b94a9d9741a5a52e226119b3080ae7390408a18a
```

The plotting script refuses to render if any digest differs.
