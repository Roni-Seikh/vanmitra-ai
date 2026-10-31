"""CSV and text exports; traceability record with explicit information-status labels."""
import config


def df_to_csv(df):
    return df.to_csv(index=False).encode("utf-8")


def info_status(batch):
    """Each line: (field, value, status). Status: verified / documented / user-reported / unavailable."""
    def st(status_field, value):
        return batch[status_field] if value else "unavailable"
    return [
        ("Batch ID", batch["batch_id"], "system-generated"),
        ("Product", batch["product"], "user-reported"),
        ("Collection date", batch["collection_date"], "user-reported"),
        ("Collection region", batch["region"], st("provenance_status", batch["region"])),
        ("Quantity", f"{batch['quantity']:g} {batch['unit']}", "user-reported"),
        ("Storage", batch["storage_type"], "user-reported"),
        ("Packaging", batch["packaging_type"], "user-reported"),
        ("Storage temperature (°C)", batch["storage_temp_c"] if batch["storage_temp_c"] is not None else "—",
         "user-reported" if batch["storage_temp_c"] is not None else "unavailable"),
        ("Storage humidity (%)", batch["storage_humidity_pct"] if batch["storage_humidity_pct"] is not None else "—",
         "user-reported" if batch["storage_humidity_pct"] is not None else "unavailable"),
        ("Producer group", batch["producer_group"] or "—", "user-reported" if batch["producer_group"] else "unavailable"),
        ("Provenance documentation", batch["provenance_ref"] or "—", batch["provenance_status"]),
        ("Sustainability documentation", batch["sustainability_doc_ref"] or "—", batch["sustainability_doc_status"]),
    ]


def batch_summary_text(batch, assessment=None):
    lines = [f"{config.APP_NAME} — Batch record ({config.TEAM})", "=" * 56]
    lines += [f"{k}: {v}  [{s}]" for k, v, s in info_status(batch)]
    if batch.get("handling_notes"):
        lines.append(f"Handling notes: {batch['handling_notes']}  [user-reported]")
    if assessment:
        lines += ["", f"Latest screening level: {assessment['level']} (score {assessment['score']}) — "
                      f"{assessment['method']}", "Limitations: " + assessment["limitations"]]
    if batch.get("is_sample"):
        lines.append("\nNOTE: SAMPLE record — illustrative demonstration data.")
    lines += ["", "Status 'verified' appears only when a verifier is named by the user; this app does not verify "
              "data independently. The QR code is only a lookup link.", config.DISCLAIMER]
    return "\n".join(lines)
