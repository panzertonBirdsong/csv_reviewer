"""Job-application workspace on top of the existing tracker columns."""
import re
import subprocess
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

import streamlit as st

JOB_COLUMNS = {"Company", "Role", "location", "ddl", "added by GPT or manually",
               "resume&story ready", "export folder path", "submitted", "job link"}
STATUS_OPTIONS = ["Keep current", "To apply", "Submitted", "Interview", "Offer", "Rejected", "On hold", "Skipped", "Not going to submit"]
APPLIED = {"Submitted", "Interview", "Offer", "Rejected"}


def is_job_tracker(headers):
    return JOB_COLUMNS.issubset(headers)


def application_status(value):
    """Classify leading status; an old duplicate warning must not undo a new status."""
    value = value.strip().casefold()
    first = value.split("\n", 1)[0]
    for prefix, label in [("interview", "Interview"), ("offer", "Offer"), ("rejected", "Rejected"),
                          ("on hold", "On hold"), ("skipped", "Skipped"), ("not going to submit", "Not going to submit"), ("to apply", "To apply")]:
        if first.startswith(prefix):
            return label
    if re.match(r"^(yes\b|true\b|1$|applied\b|submitted\b)", first):
        # Existing email confirmations may include their rejection on the same line.
        return "Rejected" if "rejected" in first else "Submitted"
    if "possible duplicate" in value or value.startswith("unknown"):
        return "Possible duplicate"
    return "To apply"


def update_status(history, status, when):
    if status == "Keep current":
        return history
    first = "Yes - submitted" if status == "Submitted" else status
    new = f"{first} {when.isoformat()}"
    return new + ("\n" + history.strip() if history.strip() else "")


def matches_queue(row, queue):
    status = application_status(row["submitted"])
    return (queue == "All jobs" or status == queue or
            (queue == "Applied / outcomes" and status in APPLIED))


def job_url(value):
    value = value.strip()
    parsed = urlparse(value)
    return value if parsed.scheme in {"http", "https"} and parsed.netloc else None


def packet_folder(value, tracker):
    if not value.strip():
        return None
    path = Path(value.strip()).expanduser()
    return path if path.is_absolute() else Path(tracker).parent / path


def answer_sections(text):
    pieces = re.split(r"^## (.+)\s*$", text, flags=re.M)
    return [(title.strip(), body.strip()) for title, body in zip(pieces[1::2], pieces[2::2])]


def read_text(path):
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        st.info(f"Could not read {path.name}: {error}")
        return None


def open_local(path):
    try:
        if sys.platform != "darwin":
            st.info(f"Open this path on your computer: {path}")
            return
        subprocess.run(["open", str(path)], check=True, capture_output=True, timeout=10)
    except (OSError, subprocess.SubprocessError) as error:
        st.error(f"Could not open the file: {error}")


def render_application(rows, index, visible, save_row):
    ss = st.session_state
    row = rows[index]
    status = application_status(row["submitted"])
    folder = packet_folder(row["export folder path"], ss.output)
    position = visible.index(index)
    st.subheader(row["Company"])
    st.markdown(f"### {row['Role']}")
    st.caption(f"{row['location']}  ·  Deadline: {row['ddl'] or 'Not stated'}  ·  Job {position + 1} of {len(visible)} in this view")
    if status == "Possible duplicate":
        st.warning("Possible duplicate: company-level application evidence exists. Review the application history before applying to this role.")
    elif status in APPLIED:
        st.info(f"Application status: {status}")
    elif status in {"On hold", "Skipped", "Not going to submit"}:
        st.info(f"Application status: {status}")
    st.caption("Preparation: " + (row["resume&story ready"] or "Not recorded"))
    a, b, c = st.columns(3)
    url = job_url(row["job link"])
    if url:
        a.link_button("Open application ↗", url, type="primary", width="stretch")
    else:
        a.warning("No valid application link.")
    pdf = folder / 'resume.pdf' if folder else None
    if pdf and pdf.is_file():
        try:
            pdf_data = pdf.read_bytes()
            safe_company = re.sub(r'[^A-Za-z0-9_-]+', '_', row['Company']).strip('_')
            b.download_button("Download résumé", pdf_data, f"Zetong_Pan_Resume_{safe_company}.pdf", "application/pdf", width="stretch", on_click="ignore")
        except OSError as error:
            pdf_data = None
            b.error(f"Cannot read résumé: {error}")
    else:
        pdf_data = None
        b.button("Résumé unavailable", disabled=True, width="stretch")
    if c.button("Open materials folder", disabled=not folder or not folder.is_dir(), width="stretch"):
        open_local(folder)

    with st.form(f"application_{index}_{ss.revision}"):
        left, right = st.columns([3, 1])
        choice = left.selectbox("Update status", STATUS_OPTIONS)
        when = right.date_input("Status date", value=date.today())
        with st.expander("Application history / notes", expanded=status == "Possible duplicate"):
            history = st.text_area("History and notes", value=row['submitted'], height=110,
                help="New statuses are added above this history. You can add notes here; they are saved in the existing submitted column.")
        st.caption("After submitting on the employer’s website, mark it here. Status changes are saved only when you press a button below.")
        p, s, n, skip, done = st.columns([1.15, 1, 1.1, 1.85, 1.75])
        previous = p.form_submit_button("Save & Previous", disabled=position == 0, width="stretch")
        save = s.form_submit_button("Save status", width="stretch")
        next_job = n.form_submit_button("Save & Next", disabled=position == len(visible)-1, width="stretch")
        not_submitting = skip.form_submit_button("Not going to submit & next", width="stretch")
        submitted = done.form_submit_button("Mark submitted & next", type="primary", width="stretch")
    if previous or save or next_job or submitted or not_submitting:
        edited = dict(row)
        selected_status = 'Not going to submit' if not_submitting else 'Submitted' if submitted else choice
        edited['submitted'] = update_status(history, selected_status, when)
        if save_row(index, edited):
            if previous:
                ss.current = visible[position-1]
            elif next_job or submitted or not_submitting:
                ss.current = visible[min(position+1,len(visible)-1)]
            ss.revision += 1
            ss.notice = f"Saved {row['Company']} — {row['Role']}."
            st.rerun()

    resume_tab, answers_tab, notes_tab, details_tab = st.tabs(["Résumé", "Answer drafts", "Job notes", "Tracker details"])
    with resume_tab:
        if pdf_data:
            if st.button("Open résumé in Preview"):
                open_local(pdf)
            try:
                st.pdf(pdf_data, height=850, key=f'resume_{index}')
            except ImportError:
                st.info("Use Download résumé or Open résumé in Preview. Install streamlit-pdf to preview inside the app.")
        else:
            st.info("No résumé PDF found in this job’s materials folder.")
        if folder and (folder/'resume.txt').is_file():
            with st.expander("Résumé text — copy for application fields"):
                content = read_text(folder/'resume.txt')
                if content:
                    st.code(content, language=None, wrap_lines=True)
    with answers_tab:
        if folder and (folder/'answers.md').is_file():
            content = read_text(folder/'answers.md')
            if content:
                st.caption("Use the copy button on each answer. Prompts labeled anticipated may differ from the employer’s form.")
                st.download_button("Download answer drafts", content, f"{folder.name}-answers.md", "text/markdown", on_click="ignore")
                for title, body in answer_sections(content):
                    with st.expander(title, expanded=not title.casefold().startswith('evidence')):
                        if title.casefold().startswith('evidence'):
                            st.markdown(body)
                        else:
                            st.code(body, language=None, wrap_lines=True)
                with st.expander("Full answer document"):
                    st.markdown(content)
        else:
            st.info("No answer drafts found for this job.")
    with notes_tab:
        if folder and (folder/'job_notes.md').is_file():
            content = read_text(folder/'job_notes.md')
            if content:
                st.markdown(content)
        else:
            st.info("No job notes found for this job.")
    with details_tab:
        st.table({"Field":list(row.keys()), "Saved value":list(row.values())})
        if folder:
            st.caption("Materials folder")
            st.code(str(folder), language=None)
        st.caption("Use Record editor in the sidebar to change job details or file paths.")
