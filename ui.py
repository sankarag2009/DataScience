import os, json, requests, streamlit as st
API = os.getenv("SILICOBIOSCREEN_API_URL", "http://127.0.0.1:8000").rstrip("/")
st.set_page_config(page_title="SilicoBioScreen", page_icon="🧬", layout="wide")
st.title("🧬 SilicoBioScreen")
st.caption("Drug–patient research pre-screening prototype")
st.warning("Use synthetic/de-identified data only. This is not a validated clinical tool and must not be used to enroll or treat patients.")

def get(path):
    try:
        r=requests.get(API+path,timeout=10); r.raise_for_status(); return r.json()
    except Exception as e:
        st.error(f"API unavailable or request failed: {e}. Start FastAPI first."); return []

def post(path, data=None):
    try:
        r=requests.post(API+path,json=data or {},timeout=15)
        if not r.ok: st.error(f"API {r.status_code}: {r.text}"); return None
        return r.json()
    except Exception as e:
        st.error(f"API request failed: {e}"); return None

tabs=st.tabs(["Overview","Candidates","Drugs","Protocols","Screen","Feedback & Metrics","Audit"])
with tabs[0]:
    cols=st.columns(3)
    cs=get("/candidates"); ds=get("/drugs"); ps=get("/protocols")
    cols[0].metric("Candidates",len(cs)); cols[1].metric("Drug profiles",len(ds)); cols[2].metric("Protocols",len(ps))
    st.markdown("**Workflow:** create candidate → define drug target → configure protocol → screen → review explanation → record verification feedback.")
    if st.button("Create synthetic demo data"):
        result=post("/demo/seed")
        if result: st.success(result["message"]); st.json(result); st.rerun()

with tabs[1]:
    st.subheader("Add candidate")
    with st.form("candidate"):
        external_id=st.text_input("Synthetic/de-identified ID","TEST-001")
        diagnosis=st.text_input("Diagnosis label/code","metastatic_colorectal_cancer")
        stage=st.text_input("Disease stage","metastatic")
        lines=st.number_input("Prior therapy lines",0,50,2)
        ecog=st.selectbox("ECOG score",[0,1,2,3,4,5])
        biomarkers=st.text_area("Biomarkers JSON",'{"TARGET_BIOMARKER":"POSITIVE"}')
        labs=st.text_area("Labs JSON",'{"egfr":90}')
        comorb=st.text_area("Comorbidities JSON list","[]")
        meds=st.text_area("Medications JSON list","[]")
        allergies=st.text_area("Allergies JSON list","[]")
        history=st.text_area("History JSON",'{"record_age_days":30}')
        if st.form_submit_button("Save candidate"):
            try:
                p={"external_id":external_id,"diagnosis":diagnosis,"disease_stage":stage or None,
                   "prior_therapy_lines":int(lines),"ecog_score":float(ecog),"biomarkers":json.loads(biomarkers),
                   "labs":json.loads(labs),"comorbidities":json.loads(comorb),"medications":json.loads(meds),
                   "allergies":json.loads(allergies),"history":json.loads(history)}
                out=post("/candidates",p)
                if out: st.success(f"Saved candidate #{out['id']}"); st.json(out)
            except Exception as e: st.error(f"Check JSON: {e}")
    st.dataframe(get("/candidates"),use_container_width=True)

with tabs[2]:
    st.subheader("Add investigational drug profile")
    with st.form("drug"):
        name=st.text_input("Drug name","Research Drug X")
        code=st.text_input("Development code","RD-X-001")
        ingredient=st.text_input("Active ingredient","To be confirmed")
        target=st.text_input("Molecular target","Example target")
        attr=st.text_input("Biomarker key in candidate record","TARGET_BIOMARKER")
        moa=st.text_area("Mechanism of action","Evidence-supported description")
        clearance=st.text_area("Clearance pathways JSON",'{"hepatic":"unknown","renal":"unknown"}')
        ddi=st.text_area("CYP/DDI profile JSON list","[]")
        safety=st.text_area("Safety liabilities JSON list","[]")
        if st.form_submit_button("Save drug"):
            try:
                p={"name":name,"development_code":code or None,"active_ingredient":ingredient or None,
                   "molecular_target":target,"target_attribute":attr,"mechanism_of_action":moa,
                   "clearance_pathways":json.loads(clearance),"cyp_ddi_profile":json.loads(ddi),
                   "safety_liabilities":json.loads(safety)}
                out=post("/drugs",p)
                if out: st.success(f"Saved drug #{out['id']}"); st.json(out)
            except Exception as e: st.error(f"Check JSON: {e}")
    st.dataframe(get("/drugs"),use_container_width=True)

with tabs[3]:
    st.subheader("Configure inclusion, exclusion, and validation rules")
    drugs=get("/drugs")
    if not drugs: st.info("Create a drug or seed demo data first.")
    else:
        dmap={f"{x['id']} — {x['name']}":x for x in drugs}
        with st.form("protocol"):
            name=st.text_input("Protocol name","Study Protocol A")
            version=st.text_input("Protocol version","1.0")
            selected=st.selectbox("Drug",list(dmap))
            inc=st.text_area("Inclusion rules JSON",'[{"id":"INC-1","field":"diagnosis","operator":"EQUALS","value":"metastatic_colorectal_cancer","reason":"Diagnosis must match"}]')
            exc=st.text_area("Exclusion rules JSON",'[{"id":"EXC-1","field":"comorbidities","operator":"CONTAINS","value":"protocol_prohibited_condition","reason":"Protocol exclusion"}]')
            val=st.text_area("Additional validation JSON",'[{"id":"VAL-1","field":"history.record_age_days","operator":"LESS_THAN_OR_EQUAL","value":180,"reason":"Record recency"}]')
            if st.form_submit_button("Save protocol"):
                try:
                    p={"name":name,"version":version,"drug_id":dmap[selected]["id"],"inclusion":json.loads(inc),
                       "exclusion":json.loads(exc),"validation":json.loads(val),"active":True}
                    out=post("/protocols",p)
                    if out: st.success(f"Saved protocol #{out['id']}"); st.json(out)
                except Exception as e: st.error(f"Check JSON: {e}")
    st.dataframe(get("/protocols"),use_container_width=True)

with tabs[4]:
    st.subheader("Screen a candidate")
    cs,ds,ps=get("/candidates"),get("/drugs"),get("/protocols")
    if not cs or not ds or not ps: st.info("Create the required records or use demo data.")
    else:
        cm={f"{x['id']} — {x['external_id']}":x for x in cs}
        dm={f"{x['id']} — {x['name']}":x for x in ds}
        pm={f"{x['id']} — {x['name']} v{x['version']}":x for x in ps}
        with st.form("screen"):
            c=st.selectbox("Candidate",list(cm)); d=st.selectbox("Drug",list(dm)); p=st.selectbox("Protocol",list(pm))
            if st.form_submit_button("Run screening"):
                out=post("/screenings",{"candidate_id":cm[c]["id"],"drug_id":dm[d]["id"],"protocol_id":pm[p]["id"]})
                if out:
                    a,b,cx=st.columns(3)
                    a.metric("Target",out["target_status"]); b.metric("Safety",out["safety_status"]); cx.metric("Eligibility",out["eligibility_status"])
                    st.write("**Decision:**",out["decision"])
                    st.write("**Reasons**")
                    for reason in out["reasons"]: st.write("- "+reason)
                    st.dataframe(out["rule_results"],use_container_width=True)
    st.subheader("Screening history"); st.dataframe(get("/screenings"),use_container_width=True)

with tabs[5]:
    st.subheader("Record confirmatory feedback")
    ss=get("/screenings")
    if ss:
        sm={f"{x['id']} — candidate {x['candidate_id']} / {x['eligibility_status']}":x for x in ss}
        with st.form("feedback"):
            chosen=st.selectbox("Screening",list(sm))
            outcome=st.selectbox("Bench outcome",["ACCEPTED","REJECTED"])
            root=st.selectbox("Root cause",["","TARGET_MUTATION_ABSENT","LATENT_ORGAN_COMPROMISE","CONCURRENT_PROHIBITED_MEDICATION","WASHOUT_PERIOD_UNMET","CLINICAL_PERFORMANCE_FAIL","OTHER"])
            reviewer=st.text_input("Reviewer role/alias","research-reviewer")
            notes=st.text_area("Notes (no patient identifiers)")
            if st.form_submit_button("Save feedback"):
                out=post("/feedback",{"screening_id":sm[chosen]["id"],"outcome":outcome,"root_cause":root or None,
                                      "reviewer":reviewer,"notes":notes or None})
                if out: st.success("Feedback saved"); st.json(out)
    else: st.info("Run a screening before adding feedback.")
    st.json(get("/metrics"))

with tabs[6]:
    st.subheader("Audit events"); st.dataframe(get("/audit"),use_container_width=True)
