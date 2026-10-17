#!/usr/bin/env bash
# Downloads the public test documents and the public prompt-injection benchmark into $REAL_DATA_DIR (default ./real_data).
# Documents are NOT committed to the repository (licences differ); fetch them yourself with this script.
set -euo pipefail
D="${REAL_DATA_DIR:-./real_data}"; UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Version/17.0 Safari/605.1.15"
dl() { mkdir -p "$D/realdocs/$1"; curl -fsSL -m 120 -A "$UA" -o "$D/realdocs/$1/$2" "$3"; echo "ok  $2  $(wc -c < "$D/realdocs/$1/$2") bytes"; }
dl hr_fmla      hr_fmla_factsheet.pdf               "https://prod.lsa.umich.edu/content/dam/lsa-site-assets/documents/human-resources/LaborLawNotices/Family-and-Medical-Leave-Act-fact-sheet.pdf"  # US DOL Fact Sheet #28 (public domain), copy hosted by U. Michigan
dl hr_unt       hr_unt_leave_policy.pdf             "https://policy.unt.edu/sites/default/files/05.069%20Leave%20of%20Absence%20without%20Pay_0.pdf"                                              # University of North Texas policy 05.069
dl gen_osha     general_osha3021_workers_rights.pdf "https://labor.vermont.gov/src/sites/labor/files/doc_library/osha3021-Workers-Rights.pdf"                                                      # OSHA 3021 (2011 edition, public domain), copy hosted by Vermont DOL
dl fin_irs463   fin_irs_pub463_travel_expenses.pdf  "https://www.irs.gov/pub/irs-pdf/p463.pdf"                                                                                                   # IRS Publication 463 (public domain)
dl fin_watravel fin_wa_travel_policies.docx         "https://des.wa.gov/sites/default/files/2025-05/Travel-policies-and-related-issues_0.docx"                                                    # Washington State DES (DOCX with a table)
dl legal_apache legal_apache_license_2.txt          "https://www.apache.org/licenses/LICENSE-2.0.txt"                                                                                             # Apache License 2.0
# Public prompt-injection benchmark: deepset/prompt-injections (Apache-2.0), via the Hugging Face datasets server
mkdir -p "$D/deepset"
for split in train test; do off=0
  while :; do f="$D/deepset/rows_${split}_$off.json"
    curl -fsSL -m 60 "https://datasets-server.huggingface.co/rows?dataset=deepset%2Fprompt-injections&config=default&split=$split&offset=$off&length=100" -o "$f"
    n=$(python3 -c "import json,sys;print(len(json.load(open('$f')).get('rows',[])))"); [ "$n" -gt 0 ] || { rm -f "$f"; break; }
    off=$((off+100)); [ "$n" -lt 100 ] && break
  done
done
echo "dataset files: $(ls "$D/deepset" | wc -l)"
