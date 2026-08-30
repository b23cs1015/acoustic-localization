import type {
  MeasurementStatus
} from "../types";

interface Props {
  status: MeasurementStatus;
}

const messages: Record<
  MeasurementStatus,
  string
> = {
  idle: "Ready for measurement.",
  requesting:
    "Requesting microphone access...",
  recording:
    "Playing chirp and recording audio...",
  processing:
    "Sending recording to the server and running analysis...",
  success:
    "Measurement completed successfully.",
  error:
    "The measurement could not be completed."
};

export default function StatusCard({
  status
}: Props) {
  return (
    <div
      className={`status-card status-${status}`}
    >
      <div className="status-dot" />

      <span>
        {messages[status]}
      </span>
    </div>
  );
}