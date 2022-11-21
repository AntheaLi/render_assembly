# PyPbrt: a Python wrapper for Pbrt-v3

## Recommended systems
- Ubuntu 18.04
- (Mini)conda 4.8.4 or higher
- GCC 7.5 (Other versions might work too but we tested the codebase with 7.5 only)

## Installation
```
git clone --recursive https://github.com/mit-gfx/py_pbrt.git
cd py_pbrt
conda env create -f environment.yml
conda activate py_pbrt
./install.sh
```

## Run
**add desired shape / obj to asset folder**

*(for folder structure see `cd asset/motions/` or you can simply rename your folder `mv <your folder > motions` )*

*(for multi part shapes folder structure should be motions/<sequence_i>/<frame_i>/<*.obj>)

*(for multi part shapes folder structure should be motions/<shape_i>/<frame_i>/<*.obj>)

**render video / frame sequences:**

**with checkboard floor**
```
python render_assembly.py --export-video --ckbd --folder 6_0
```

**with white background**
```
python render_assembly.py --export-video --folder 6_0
```

**with white background and save transparent background:**
```
python render_assembly.py --export-video --no-bg --folder 6_0
```

**render a single frame**
```
python render_assembly.py --single-frame  --no-bg --folder 6_0 --frame 0
```
# render_assembly
