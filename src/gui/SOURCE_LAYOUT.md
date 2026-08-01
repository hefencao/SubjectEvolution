# GUI v20 source layout

```text
src/gui/
├─ include/eco/
│  ├─ mapped_file.hpp
│  ├─ protocol.hpp
│  ├─ renderer.hpp
│  ├─ shared_reader.hpp
│  └─ social_loop.hpp
├─ src/
│  ├─ main.cpp                  runtime, launcher and observation UI
│  ├─ mapped_file.cpp
│  ├─ shared_reader.cpp
│  ├─ social_loop.cpp
│  ├─ renderer*.cpp             split renderer implementation
│  └─ render/
│     ├─ renderer_internal.hpp
│     └─ renderer_state.hpp
└─ renderer_sources.cmake
```

The v20 launcher remains in `main.cpp`; no extra production module was created
for this limited startup iteration.
