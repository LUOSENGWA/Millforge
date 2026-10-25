## Dual-Channel Reporting (condensed load · full text = protocol §06-3)

| Channel | Duty | Content |
|------|------|------|
| **Full report in the project room** (archive floor) | visible to the whole team + human, structured | full conclusions / output paths / open issues / next steps |
| **Notice on the originating channel** (delivery floor) | the channel the human actually uses | one line: done + key conclusions + project-room pointer |

- Single-team task: the originating channel is the floor
- Cross-team task (single_user only): both channels — full report in the project room @human + originating-channel notice
- Originating channel = the reply_route recorded at dispatch time (never guessed ad hoc)
- **Delivery is an L2 mechanism (CAP-NOTIFY delivery_report); content generation is L3** — what is lost can be rebuilt from CAP-STATE; never rely on "remembering to send"
- **File delivery = reporting**: publishing an artifact / result.md / long-output dump must be accompanied by an @-mention text summary (conclusions + path + next step); a file event without @ notifies nobody (silent, i.e. not reported)
