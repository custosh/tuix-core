# 🧱 TUIX Core 0.1.0

> ⚠️ **ATTENTION:**  
> This version of the library is an **MVP (Minimal Viable Project)** release.  
> Many of the implemented functions exist in the codebase but are **not yet actively used**.  
> This version serves as the foundation for upcoming releases.

---

## 🧩 Overview

**TUIX** is a modular terminal UI engine inspired by web technologies.  
It introduces a **DOM-like component system**, a **layout engine**, and a **buffer-based rendering pipeline** for building structured and styled terminal interfaces.

---

## 🚀 Installation

You can install this library using:

```bash
pip install tuix-core
```

---

# ⚡ Example Usage

Even though this MVP version is limited, here’s a small example showing what it can currently do:

```python
from tuix.core import TuixEngine as Tuix

# Initialize the main application engine
app = Tuix()

# Create a new component of type "choice"
app.components.create(object_type="choice", object_id="choice")

# Set component properties
app.components.set_property(object_id="choice", param="label", value="Test")

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
app.layout.margin_mode(object_id="choice", param=["margin_top", "margin_left"], mode="centered")

# Render the layout to the terminal
app.render.draw()
```

🖥️ This renders a simple `choice` component in the terminal, centered both vertically and horizontally.

---

# ⚙️ Future Plans

Both the `LayouEngine` and `RenderEngine` will be rewritten in upcoming versions to create a far more powerful and flexible structure(🤫 won’t spoil the details yet).

---

# 📜 License

MIT License © 2025 custosh

```text
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

```
