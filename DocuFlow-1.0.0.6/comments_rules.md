# Project Commenting Style Rules

This document defines the standard commenting practices for all code within the project. Following these rules ensures **consistency, readability, and maintainability**.

---

## 1. JavaScript

### 1.1 File Header

Every `.js` file must start with the following header:

```js
// [File Path e.g., js/main.js]
/**
 * Project: [Project Name]
 * File:  [File Name e.g., main.js]
 * Created: [YYYY-MM-DD]
 * Author: @lewopxd
 *
 * Description:
 * [Brief and clear description of the file's purpose.]
 */
```

### 1.2 Logical Code Blocks

Use these tags to group related functions or logic for easier navigation.

```js
//-------------------------------------------------------------
//-------------[   BLOCK NAME   ]------------------------------
//-------------------------------------------------------------
// ... code ...
//--------------------------------------> END [ BLOCK NAME ... ]
```

### 1.3 Function Documentation

Each function must be preceded by a JSDoc-style comment:

```js
/**
 * [Brief description of what the function does.]
 * @param {[type]} [name] - [Parameter description.]
 * @returns {[type]} [Description of the returned value.]
 */
```

### 1.4 General Rules

* **Language:** All comments must be written in English.
* **Clarity:** Be precise and non-redundant. Explain the *why*, not the *what*.
* **Consistency:** Apply this guide uniformly across all files.

---

## 2. CSS

### 2.1 File Header

Every `.css` file must begin with this metadata block:

```css
/*
 * Project: [Project Name]
 * File:  [File Name e.g., main.css]
 * Created: [YYYY-MM-DD]
 * Author: @lewopxd
 *
 * Description:
 * [Brief and clear description of the stylesheet's purpose.]
 */
```

### 2.2 Logical Blocks

Separate major stylesheet sections for better organization.

```css
/*=============================================
=            BLOCK NAME                     =
=============================================*/
/* ... rules ... */
/*=====  End of BLOCK NAME  ======*/
```

### 2.3 Style Group Comments

Add a short comment before grouped component rules:

```css
/*-- Component: Primary Button --*/
.btn-primary { ... }
.btn-primary:hover { ... }
.btn-primary.is-disabled { ... }
```

### 2.4 General Rules

* **Language:** English only.
* **Clarity:** Be concise. Good class naming reduces the need for comments.
* **Consistency:** Apply this guide uniformly across all project files.

---

## 3. Python

### 3.1 File Header (Module Docstring)

Each `.py` file should start with an optional shebang, required encoding, and a module-level docstring:

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Project: [Project Name]
File:  [File Name e.g., utils.py]
Created: [YYYY-MM-DD]
Author: @lewopxd

Description:
[Brief and clear description of the module's purpose.]
"""
```

### 3.2 Logical Code Blocks

Group related functionality for clarity.

```python
# -------------------------------------------------------------
# -------------------[   BLOCK NAME   ]------------------------
# -------------------------------------------------------------
# ... code ...
# --------------------------------------> END [ BLOCK NAME ... ]
```

### 3.3 Function and Class Documentation (Docstrings)

Follow **Google Style** (PEP 257 compliant).

**Function Example:**

```python
def my_function(param1, param2):
    """[Brief one-line description of what the function does.]

    [More detailed explanation if necessary.]

    Args:
        param1 (str): [Description of parameter 1.]
        param2 (int): [Description of parameter 2.]

    Returns:
        bool: [Description of return value.]

    Raises:
        ValueError: [Condition under which this exception is raised.]
    """
    if param2 < 0:
        raise ValueError("param2 cannot be negative")
    return True
```

**Class Example:**

```python
class MyClass:
    """[Brief class description.]

    Attributes:
        attr1 (str): [Description of attribute.]
    """

    def __init__(self, attr1):
        """Initializes MyClass instance."""
        self.attr1 = attr1
```

### 3.4 General Rules

* **Language:** English only.
* **Clarity:** Be precise. Follow PEP 8 and PEP 257. Explain the *why*, not the *what*.
* **Consistency:** Apply this style across all project files.

---

## 4. HTML

### 4.1 Core Rule

No comments (`<!-- -->`) should be included in HTML files.

### 4.2 Rationale

HTML must be self-explanatory through **semantic, clean markup**. Comments can expose internal information and add unnecessary file weight.
