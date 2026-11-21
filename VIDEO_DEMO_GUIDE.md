# MeetFlow AI — recording guide

This guide prepares the existing demo workspace for the supplied 2:35 voiceover. The three preloaded meetings are **demo fallback data**; their source label is visible in the app. The separate transcript below is for demonstrating an actual Gemini call.

## Before recording

1. Start the backend and frontend using the instructions in [README.md](README.md). Open `http://localhost:5173`.
2. Enter your name, choose **Organization Admin**, and select **Start demo**. This creates a private sandbox with Monday Planning, Wednesday Review and Friday Execution Review. If you already have a sandbox open, **Reset demo** restores the recording data but removes changes in that sandbox; keep anything you need before resetting.
3. Check the backend configuration for a valid Gemini key. In demo mode GitHub is disabled, but Gemini still uses the backend key. The seeded meetings are marked **Demo fallback data**; they were not processed live by Gemini.
4. The launch decisions are December 10 and December 15. The year is chosen automatically so the launch is upcoming; task deadlines are relative to the current date. The conflict starts unresolved and the older decision remains active.
5. Generate Sarah's digest once before recording to check that Gemini is available. Responses may take time or fail if the service is busy. Do not present a fallback or failed response as live Gemini output.

## Transcript for the live meeting

Use the title **Customer Onboarding**, today's meeting date, and the **Product Team** department. Paste the following transcript, choose **Save meeting**, then **Process with agent**:

```text
Morgan: We agreed to prepare a customer onboarding guide for the product launch.
Sarah: I will draft the onboarding guide by December 2, 2026.
Alex: I will review the onboarding guide by December 4, 2026.
```

If recording in a later year, change the two years to match the year shown in Decision Memory. Once processing finishes, show the **Gemini analysis** label, summary, speakers, decisions, tasks and transcript. Wait for the actual result; edit out the wait in the video if needed. AI output can vary, so review it before recording the final take.

## Suggested shots

| Time | Screen and action |
| --- | --- |
| 0:00–0:15 | Show the overview and the seeded meeting, task and open-conflict counts. |
| 0:15–0:35 | Briefly show the sidebar and overview. |
| 0:35–0:55 | On **Meetings**, paste the transcript above, save it, and process it. Cut to the result with the **Gemini analysis** label. |
| 0:55–1:15 | Open **Decision Memory**. Search for `launch` to show the earlier active decision and the pending update. |
| 1:15–1:40 | Open **Conflicts**. Show December 10 and December 15, the meeting names, Morgan's quotations and the explanation. Show the resolution buttons. If desired, select **Supersede old decision** and return to Decision Memory to show the preserved history. |
| 1:40–2:00 | Open **Tasks**. Show Sarah and Alex on the board, the pending documentation review and the unassigned deployment checklist. Approve the documentation review while leaving the checklist unassigned. |
| 2:00–2:15 | Show **Reminders**, then choose Sarah under **Weekly Digest** and generate a summary. Wait for the result and show its source label. |
| 2:15–2:35 | Return to the overview for the closing. |

To make another take, use **Reset demo** and repeat. Reset affects only the current sandbox and does not reset the session's AI usage limit. A new demo starts with a fresh sandbox.
