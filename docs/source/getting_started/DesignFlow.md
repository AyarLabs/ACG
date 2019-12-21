# Design Flow

TODO: Explain high level architecture of ACG 
1. All layout scripts are written as classes which subclass `AyarLayoutGenerator`
2. Your subclass of `AyarLayoutGenerator` defines how the layout should be drawn in terms of parameters that you define and technology constants
3. `AyarDesignManager` configures details about your technology, receives parameters from the user, and runs the generator to create an output layout.
4. Talk about spec files, and why they are useful
