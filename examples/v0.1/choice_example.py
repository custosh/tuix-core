from tuix.core import TuixEngine as Tuix

# Initialize the main application engine
app = Tuix()

# Create a new component of type "choice"
app.components.create(type="choice", id="choice")

# Set component properties
app.components.set_property(id="choice", param="label", value="Test")

# Define a list of choices with actions
app.components.set_property(
    object_id="choice",
    param="choices",
    value=[
        [
            {"name": "Test", "action": "pass"},
            {"name": "Test", "action": "pass"}
        ]
    ]
)

# Align the component to the center using margin mode
app.layout.margin_mode(id="choice", param=["margin_top", "margin_left"], mode="centered")

# Render the layout to the terminal
app.render.draw()

