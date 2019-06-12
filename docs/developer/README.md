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
We are using pdoc for automatic generation of documentation from the code base.
Pdoc provides a simple solution with an aesthetically please enough result. An
alternative tool is Sphinx, which requires much more upfront configuration, but 
also offers greater flexibility.



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
