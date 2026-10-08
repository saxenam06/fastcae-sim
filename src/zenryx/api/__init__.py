"""What the web UI reads.

`snapshot` builds one deterministic payload from the records: the contracts today, and the
campaigns, designs, evaluations and datapoints once the agent and the judge make them. It is
written to a file for the UI to bundle; the API (PLT-5) will serve the same payload.
"""
