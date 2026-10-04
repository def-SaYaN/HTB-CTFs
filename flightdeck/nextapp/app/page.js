import { recordDeployNote } from "./actions";

export default function Page() {
  return (
    <main style={{ fontFamily: "system-ui", padding: 40 }}>
      <h1>FlightDeck Admin</h1>
      <p>Internal deploy console. Authorized operators only.</p>
      <form action={recordDeployNote}>
        <label>
          Deploy note:{" "}
          <input type="text" name="note" defaultValue="" />
        </label>
        <button type="submit">Save</button>
      </form>
    </main>
  );
}
