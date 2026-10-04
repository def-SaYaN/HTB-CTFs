export const metadata = {
  title: "FlightDeck Admin",
  description: "Internal admin panel",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
