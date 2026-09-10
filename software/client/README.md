# Client Applications

The box sets up a wireless network in AP mode to allow communication. It also hosts an HTTP webserver. To control the lights, you first need to connect to the wireless network and then you need to make a request via some software tool. Examples for the linux command line tool curl are provided as are python examples that use the requests library.

The box has two modes: an automatic mode scrolling through gradients and a manual mode allowing pixel control. There is one api endpoint to get the current mode or set a new mode. There is another api endpoint for manual mode that allows pixel level control of the display. The main input is an array of length equal to the number of pixels where each element is an integer that corresponds to a color. 0 is black. 1-255 are colors sampled linearly in HSV space by stepping hue.

## curl

Assuming you have a linux computer, this is perhaps the simplest option but using it to make complex shapes on the display or write text may be tricky.

This sets the mode to manual, 1. 0 for Mode would be the color gradient:
```
curl --header "Content-Type: application/json" \
  --request POST \
  --data '{"mode":1}' \
  http://10.42.0.1:5000/mode
```

this sets the screen to be all one color, assuming the box is in manual mode already:
```
json_array=$(printf '243,%.0s' $(seq 1 4095))
json_array="${json_array}243"
curl --header "Content-Type: application/json" \
  --request POST \
  --data "{\"pixels\":[${json_array}]}" \
  http://10.42.0.1:5000/manual
```

## python

This is a more complex option and requires some setup on the comptuer but has the benefit of being cross platform (windows, mac, os) as long as the libraries used are supported on the platform (and they generally are).

This example will display the word "love" on the display with shading. It uses an open-source TTF font, Satoshi-Variable. It was tested with python3.10 but should work on most modern and older versions of python. The specific library dependencies used are in the `requirements.txt` file, but others should work too.

```
# create a virtual environment so that when we install libraries
# we do not do it for all the users
python3 -m venv venv
# activate it so that we point python commands to this environment
source venv/bin/activate
# install dependencies
python3 -m pip install -r requirements.txt
# run the script and the display should update
python3 send_txt.py
```