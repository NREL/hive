# Naming Conventions
Generally we try to adhere to [PEP-8 naming conventions](https://www.python.org/dev/peps/pep-0008/#naming-conventions),
the most relevant are repeated here:

__Class Names__: use CapWords convention (i.e. "SampleClass")

__Function and Variable Names__: lowercase with words separated by underscores 
(i.e. "number_of_monsters")

__Funcation and Method Arguments__: If a function argument's name clashes with a
reserved keyword, it is better to append a single trailing underscore rather 
than an abbreviation or spelling corruption. Synonyms where possible might even
be better (i.e. "class_" not "clss").

__Constants__: Defined on a module level and written in all capital letters with
underscores separating words (i.e. "MAX_SPEED" and "DENSITY")

There are many other valuable conventions in the PEP-8 standards linked above, 
please review if you have any questions.


# Auto Doc Generation
We are using Sphinx for automatic generation of documentation from the code base.
Sphinx is highly customizable and is the industry standard for documenting many
open source projects.

Sphinx runs in a pre-commit hook in this repo. The command line interface runs to 
generate the html documentation, which are created in hive/docs/build/html.

It is critical to include docstrings in modules, classes, methods, and functions
per the format below. Sphinx builds the documentation from these strings. Refer to the [Pandas docstrings guide](https://pandas.pydata.org/pandas-docs/stable/development/contributing_docstring.html)
for direction if it is not clear from this document.

Generally docstrings for functions and methods should look like this:

    def add(num1, num2):

        """
        Add up two integer numbers.

        This function simply wraps the `+` operator, and does not
        do anything interesting, except for illustrating what is
        the docstring of a very simple function.

        Parameters
        ----------
        num1 : int
            First number to add
        num2 : int
            Second number to add

        Returns
        -------
        int
            The sum of `num1` and `num2`

        See Also
        --------
        subtract : Subtract one integer from another

        Examples
        --------
        >>> add(2, 2)
        4
        >>> add(25, 0)
        25
        >>> add(10, -10)
        0
        """
    return num1 + num2





# Error message formatting

# Testing
## unittest
__unittest__ is the Python standard library test module. It has a simple
API and is a good introduction to testing for those with less familiarity. Docs 
are available [here](https://docs.python.org/3/library/unittest.html#module-unittest).




## don't test things twice (no subfunctions)
## unit tests for one module should never influence another



# Inputs
## Standard README formats for each (autogen user doc)
