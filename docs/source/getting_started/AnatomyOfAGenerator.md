# Anatomy of a Generator

TODO: Explain detailed information about the ALG class
1. `AyarLayoutGenerator` provides helper methods to place and manipulate shapes and hierarchically place other instances and run other generators. Consider it to be your palette of functions you can use to describe your layout procedure.
2. `get_params_info()` should be defined to set which parameters your generator expects.
3. `AyarLayoutGenerator` defines an abstractmethod `draw_layout()` which contains the layout drawing algorithm in terms of your desired parameters.

Show pictures of how a few of the key functions work 
