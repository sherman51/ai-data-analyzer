Create a Python Streamlit app that replicates the "Outbound Dashboard" layout from the attached image. Use a sample dataset to generate the visuals.
The dashboard should include:

1. Header Section:

Logo placeholder (top left) and "Outbound Dashboard" title.

Display "Past 2 weeks orders" and "Avg. Daily Orders" as KPI cards.

Display the current date (green) and "Daily Outbound Orders" count.

2. Orders Trend Chart:

A bar chart for the last 2 weeks showing "Orders Received" (green) and "Orders Cancelled" (orange).

X-axis: dates; Y-axis: order counts.

3. Month to Date Section:

Two circular gauge charts:

"Back Order" with percentage and a numeric count.

"Order Accuracy" with percentage and a numeric count.

Values are from the sample dataset.

4. Orders Breakdown Section:

A horizontal stacked bar chart for:

Back Orders (Accumulated)

Scheduled Orders

Ad-hoc Normal Orders

Ad-hoc Urgent Orders

Ad-hoc Critical Orders

Each segment should be color-coded (green, blue, yellow, orange, etc.) and labeled with counts.

5. Summary Table:

Columns: Ad-hoc Critical Orders, Ad-hoc Urgent Orders, Ad-hoc Normal Orders, Scheduled Orders, Back Orders (Accumulated).

Rows: Tpt Booked, Packed/Partial Packed, Picked/Partial Picked, Open.

Fill with sample data.

6. Design Guidelines:

Match the color theme (dark blue background, green for completed, yellow for picked, light blue for packed, peach for open).

Use Streamlit components for layout (columns, markdown, and charts).

Use Plotly for charts (bar, stacked bar, and gauge).

Include sample dataset creation inside the script so it runs standalone.

Output the complete streamlit_app.py code.
