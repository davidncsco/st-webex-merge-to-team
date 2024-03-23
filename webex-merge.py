import streamlit as st
import requests
from requests import HTTPError
import os, time

# Input token variable either from sidebar or environment variable
access_token = st.sidebar.text_input("Your Webex Access Token", os.getenv("WEBEX_ACCESS_TOKEN"))

@st.cache_data
def fetch_members(url):
    print(f'calling fetch_members {url}')
    members = []
    with st.spinner(f"Fetching memberships..."):
        while url:
            try:
                response = requests.get(url, headers=headers)
                if response.status_code == 429:
                    time.sleep(int(response.headers["Retry-After"]))
                    continue
                response.raise_for_status()
                data = response.json()
                members.extend(data['items'])
                url = response.links["next"]["url"] if response.links.get("next") else None
            except HTTPError as e:
                st.exception(e)
                break
    return members

@st.cache_data
def fetch_all_teams():
    """  Returns list of teams to which the authenticated user belongs and is moderator
    """
    url = "https://webexapis.com/v1/teams"
    
    teams = {}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        teams_data = response.json()
        for team in teams_data["items"]:
            teams[team['id']] = team['name']
        return teams
    else:
        print(f"Error fetching teams. Status code: {response.status_code}")
        return None

def filter_strings(strings, query):
    filtered_strings = [s for s in strings if query.lower() in s.lower()]
    return filtered_strings

def get_key_by_value(dictionary, target_value):
    for key, value in dictionary.items():
        if value == target_value:
            return key
    return None


def add_new_member(team_id, email):
    # Data for the new member
    data = {
         "teamId" : f"{team_id}",
         "personEmail" : f"{email}",
         "isModerator" : False
        }
    # Send POST request
    MAX_RETRIES = 3
    
    url = "https://webexapis.com/v1/team/memberships"
    retries = 0
    while True:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 429 and retries < MAX_RETRIES:
            retry_time = int(response.headers["Retry-After"])
            st.write(f"received 429 response, retry in {retry_time} secs...")
            time.sleep(retry_time)
            retries += 1
            continue
        # Check for successful response
        if response.status_code == 200:
            st.write(f"Successful!")
        else:
            st.write(f"Error adding member: {response.status_code} - {response.text}")
        break

def find_email_difference(list1, list2):
    """
    This function finds the difference between two lists of emails.
    Returns:
            - Emails present in list1 but not in list2.
    """
    # Convert lists to sets for efficient lookups
    set1 = set(list1)
    set2 = set(list2)

    # Find emails in list1 but not list2 (using difference operator)
    return list(set1.difference(set2))

def add_new_memberships_to_team(team_id,emails):
    st.write("**Adding new memberships to team**")
    container = st.container(height=150)
    for email in emails:
        with container:
            st.write(f"Adding new member with email={email}")
            add_new_member(team_id, email)
    with container:
        st.write("Done :sunglasses:")
    
if __name__ == "__main__":
    st.markdown("### Webex Space->Team Memberships Merge Tool")

    # Input source space link roomId
    source_id = st.text_input("Enter source space link id (can be copied from space link setting)")
    if source_id:
        if access_token == None:  # Must provide access token before continue
            st.write("Please provide WEBEX access token before continue.")
            st.stop()
            
        headers = { 
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        url = f"https://webexapis.com/v1/memberships?roomId={source_id}&max=1000"
        source_members = fetch_members(url)

        st.success(f"memberships: {len(source_members)} members")
        if len(source_members) > 0:
            # Now fetch all teams that to which the authenticated user belongs and select one from the list
            with st.spinner("Fetching all teams..."):
                teams = fetch_all_teams()
            
            options = [title for title in teams.values()]
            # Input field for user to enter search query
            query = st.text_input("Enter team name search:", "")
            # Filter the options based on the search query
            filtered_options = filter_strings(options, query)
            # Create dropdown selection based on filtered options
            selected_option = st.selectbox("Or select target team from this list", filtered_options)
            st.markdown(f"You selected: **{selected_option}**")
            
            target_team_id = get_key_by_value(teams, selected_option)
            url = f"https://webexapis.com//v1/team/memberships?teamId={target_team_id}&max=1000"
            target_members = fetch_members(url)
            st.success(f"memberships: {len(target_members)} members")
            
            email_list1 = [member["personEmail"] for member in source_members]
            email_list2 = [member["personEmail"] for member in target_members]
            email_list3 = find_email_difference(email_list1,email_list2)

            st.write(f"There are potentially {len(email_list3)} members to be added to target team")
            
            if (len(email_list3) > 0) and st.button("Click to add new memberships from space to team"):
                add_new_memberships_to_team(target_team_id,email_list3)

            
